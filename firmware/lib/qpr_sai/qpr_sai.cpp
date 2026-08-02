// qpr_sai.cpp — SAI1 four-channel capture, SAI2 stereo monitor output
//
// Vendor: Illicit Apothecary
// See qpr_sai.h for the clock plan and the pin-33 hazard note.

#include "qpr_sai.h"
#include <DMAChannel.h>
#include "qpr_board.h"

// set_audioClock() lives in the Audio library's utility/imxrt_hw. We do not
// want the whole Audio library linked in, so the PLL4 setup is reimplemented
// here from the same register sequence.
namespace qpr {
namespace {

// ---------------------------------------------------------------------------
// Audio PLL (PLL4)
// ---------------------------------------------------------------------------
// PLL4 = 24 MHz * (nfact + nmult/ndiv), POST_DIV_SELECT(2) = divide by 1.
// The i.MX RT1062 requires the VCO to land between 648 MHz and 1300 MHz.
FLASHMEM void setAudioPll(int nfact, int32_t nmult, uint32_t ndiv) {
  CCM_ANALOG_PLL_AUDIO = CCM_ANALOG_PLL_AUDIO_BYPASS |
                         CCM_ANALOG_PLL_AUDIO_ENABLE |
                         CCM_ANALOG_PLL_AUDIO_POST_DIV_SELECT(2) |
                         CCM_ANALOG_PLL_AUDIO_DIV_SELECT(nfact);
  CCM_ANALOG_PLL_AUDIO_NUM   = nmult & CCM_ANALOG_PLL_AUDIO_NUM_MASK;
  CCM_ANALOG_PLL_AUDIO_DENOM = ndiv  & CCM_ANALOG_PLL_AUDIO_DENOM_MASK;
  CCM_ANALOG_PLL_AUDIO &= ~CCM_ANALOG_PLL_AUDIO_POWERDOWN;
  while (!(CCM_ANALOG_PLL_AUDIO & CCM_ANALOG_PLL_AUDIO_LOCK)) { }
  // Post-divider in MISC2 set to /1.
  CCM_ANALOG_MISC2 &= ~(CCM_ANALOG_MISC2_DIV_MSB | CCM_ANALOG_MISC2_DIV_LSB);
  CCM_ANALOG_PLL_AUDIO &= ~CCM_ANALOG_PLL_AUDIO_BYPASS;
}

// 24e6 * (32 + 7680/10000) = 786,432,000 Hz exactly.
constexpr int      kPllNfact = 32;
constexpr int32_t  kPllNmult = 7680;
constexpr uint32_t kPllNdiv  = 10000;
constexpr uint32_t kPllHz    = 786432000u;

bool g_pll_started = false;
void ensureAudioPll() {
  if (g_pll_started) return;
  setAudioPll(kPllNfact, kPllNmult, kPllNdiv);
  g_pll_started = true;
}

// ---- SAI1 dividers --------------------------------------------------------
#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
constexpr uint32_t kSai1Pred = 4;   // -> root 24.576 MHz = MCLK = 128 fs
constexpr uint32_t kSai1Podf = 8;
constexpr uint32_t kSai1BclkDiv = 0;   // BCLK = MCLK / (2 * (DIV+1)) = MCLK/2
constexpr uint32_t kFrameWords = 2;    // 2 x 32-bit slots per data line
constexpr uint32_t kWordsPerFrameInBuffer = 4;  // 2 lines x 2 slots
#else
constexpr uint32_t kSai1Pred = 4;   // -> root 49.152 MHz = MCLK = 512 fs
constexpr uint32_t kSai1Podf = 4;
constexpr uint32_t kSai1BclkDiv = 0;   // BCLK = MCLK/2 = 24.576 MHz = 256 fs
constexpr uint32_t kFrameWords = 8;    // 8 x 32-bit slots, 4 carry data
constexpr uint32_t kWordsPerFrameInBuffer = 4;  // slots 4..7 masked off
#endif

// ---- SAI2 dividers (48 kHz monitor) --------------------------------------
constexpr uint32_t kSai2Pred = 4;    // -> root 12.288 MHz = 256 fs
constexpr uint32_t kSai2Podf = 16;
constexpr uint32_t kSai2BclkDiv = 1; // BCLK = root / 4 = 3.072 MHz = 64 fs

// ---------------------------------------------------------------------------
// DMA buffers. DMAMEM puts these in OCRAM (RAM2), which is cached on the
// Teensy 4.1, hence the explicit cache maintenance in the ISRs.
// ---------------------------------------------------------------------------
constexpr uint32_t kRxWordsPerHalf = cfg::kDmaFramesPerHalf * kWordsPerFrameInBuffer;
DMAMEM __attribute__((aligned(32))) uint32_t g_rx_buffer[kRxWordsPerHalf * 2];

constexpr uint32_t kTxFramesPerHalf = cfg::kMonitorBlockSamples;
constexpr uint32_t kTxWordsPerHalf  = kTxFramesPerHalf * 2;  // stereo
DMAMEM __attribute__((aligned(32))) uint32_t g_tx_buffer[kTxWordsPerHalf * 2];

DMAChannel g_rx_dma(false);
DMAChannel g_tx_dma(false);

// Deinterleaved staging for the capture callback. Lives in DTCM (fast) --
// 256 frames x 16 bytes = 4 KiB.
Frame4 g_frames[cfg::kDmaFramesPerHalf];

// Monitor block handoff: the DSP software interrupt fills one of these, the
// SAI2 DMA interrupt consumes it. Single-producer / single-consumer, one slot
// deep, guarded by a volatile flag -- no locks needed on a single core.
constexpr uint32_t kMonSlots = 3;
struct MonitorBlock {
  float left[cfg::kMonitorBlockSamples];
  float right[cfg::kMonitorBlockSamples];
};
MonitorBlock g_mon[kMonSlots];
volatile uint32_t g_mon_write = 0;   // next slot the DSP will fill
volatile uint32_t g_mon_read  = 0;   // next slot the DMA ISR will play
volatile bool     g_mon_ready[kMonSlots] = { false, false, false };

// Interrupt priorities. Lower number wins on Cortex-M7.
constexpr uint8_t kCapturePriority = 96;   // above the 128 default
constexpr uint8_t kMonitorPriority = 112;
constexpr uint8_t kDspPriority     = 208;  // well below everything else

inline int32_t slotToSample(uint32_t raw) {
  // The PCM1864 is configured for a 32-bit transmit word (TX_WLEN = 00), so
  // the 24-bit sample sits in bits 31..8 with zeros below. An arithmetic
  // shift sign-extends it into a ±2^23 int32.
  return ((int32_t)raw) >> 8;
}

inline float sampleToFloat(int32_t s) {
  return (float)s * (1.0f / 8388608.0f);  // 2^23
}

inline uint32_t floatToSlot(float v) {
  if (v >  0.999999f) v =  0.999999f;
  if (v < -0.999999f) v = -0.999999f;
  // Shift through unsigned: left-shifting a negative signed value is undefined
  // before C++20 and this builds as gnu++17.
  return (uint32_t)(int32_t)(v * 8388607.0f) << 8;
}

// ---------------------------------------------------------------------------
// SAI1 configuration
// ---------------------------------------------------------------------------
FLASHMEM void configSai1() {
  CCM_CCGR5 |= CCM_CCGR5_SAI1(CCM_CCGR_ON);
  ensureAudioPll();

  CCM_CSCMR1 = (CCM_CSCMR1 & ~CCM_CSCMR1_SAI1_CLK_SEL_MASK) |
               CCM_CSCMR1_SAI1_CLK_SEL(2);  // 2 = PLL4 (audio PLL)
  CCM_CS1CDR = (CCM_CS1CDR & ~(CCM_CS1CDR_SAI1_CLK_PRED_MASK |
                               CCM_CS1CDR_SAI1_CLK_PODF_MASK)) |
               CCM_CS1CDR_SAI1_CLK_PRED(kSai1Pred - 1) |
               CCM_CS1CDR_SAI1_CLK_PODF(kSai1Podf - 1);

  // MCLK1 is an output driven from the CCM root.
  IOMUXC_GPR_GPR1 = (IOMUXC_GPR_GPR1 & ~IOMUXC_GPR_GPR1_SAI1_MCLK1_SEL_MASK) |
                    IOMUXC_GPR_GPR1_SAI1_MCLK_DIR |
                    IOMUXC_GPR_GPR1_SAI1_MCLK1_SEL(0);

  // Pin mux. ALT3 on all four.
  CORE_PIN23_CONFIG = 3;  // MCLK1  -> PCM1864 SCKI
  CORE_PIN21_CONFIG = 3;  // RX_BCLK
  CORE_PIN20_CONFIG = 3;  // RX_SYNC (LRCLK)
  CORE_PIN8_CONFIG  = 3;  // RX_DATA0 <- PCM1864 DOUT
  IOMUXC_SAI1_RX_DATA0_SELECT_INPUT = 2;  // GPIO_B1_00_ALT3
#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
  CORE_PIN6_CONFIG  = 3;  // RX_DATA1 <- PCM1864 DOUT2 (GPIO0)
  IOMUXC_SAI1_RX_DATA1_SELECT_INPUT = 1;  // GPIO_B0_10_ALT3
#endif

  // The receiver is the clock master (BCD/FSD set on RCR2/RCR4); the
  // transmitter is synchronised to it and is otherwise unused on SAI1.
  I2S1_RMR = 0;
  I2S1_RCR1 = I2S_RCR1_RFW(4);   // DMA request once 4 words are in each FIFO
  I2S1_RCR2 = I2S_RCR2_SYNC(0) | I2S_RCR2_BCP | I2S_RCR2_BCD |
              I2S_RCR2_DIV(kSai1BclkDiv) | I2S_RCR2_MSEL(1);

#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
  // Standard I2S frame: 2 words of 32 bits, frame sync one bit early,
  // frame sync active low, MSB first.
  I2S1_RCR3 = I2S_RCR3_RCE_2CH;
  I2S1_RCR4 = I2S_RCR4_FRSZ(kFrameWords - 1) | I2S_RCR4_SYWD(32 - 1) |
              I2S_RCR4_MF | I2S_RCR4_FSE | I2S_RCR4_FSP | I2S_RCR4_FSD;
#else
  // TDM frame: 8 words of 32 bits (256 BCK), one-bit frame sync, first four
  // slots carry FLU/FRD/BLD/BRU. RMR masks slots 4..7 so they never reach
  // the FIFO and the DMA only moves the four words we care about.
  //
  // UNVERIFIED ON SILICON. This whole branch is the 96 kHz fallback and has
  // never been run against a real PCM1864. The frame-sync polarity in
  // particular is a judgement call: FSP makes the sync active low, while the
  // PCM1864 datasheet says a slave needs "a rising edge on the first bit" to
  // start a TDM frame. If t06_audio shows the ADC running but the channels
  // rotated or silent in this mode, try dropping I2S_RCR4_FSP here, and try
  // TX_TDM_OFFSET of 0 instead of 1 in the PCM1864 driver.
  I2S1_RCR3 = I2S_RCR3_RCE;
  I2S1_RCR4 = I2S_RCR4_FRSZ(kFrameWords - 1) | I2S_RCR4_SYWD(1 - 1) |
              I2S_RCR4_MF | I2S_RCR4_FSE | I2S_RCR4_FSP | I2S_RCR4_FSD;
  I2S1_RMR = 0xF0;
#endif
  I2S1_RCR5 = I2S_RCR5_WNW(32 - 1) | I2S_RCR5_W0W(32 - 1) | I2S_RCR5_FBT(32 - 1);
}

// ---------------------------------------------------------------------------
// SAI2 configuration (48 kHz stereo out to the PCM5102A)
// ---------------------------------------------------------------------------
FLASHMEM void configSai2() {
  CCM_CCGR5 |= CCM_CCGR5_SAI2(CCM_CCGR_ON);
  ensureAudioPll();

  CCM_CSCMR1 = (CCM_CSCMR1 & ~CCM_CSCMR1_SAI2_CLK_SEL_MASK) |
               CCM_CSCMR1_SAI2_CLK_SEL(2);  // PLL4
  CCM_CS2CDR = (CCM_CS2CDR & ~(CCM_CS2CDR_SAI2_CLK_PRED_MASK |
                               CCM_CS2CDR_SAI2_CLK_PODF_MASK)) |
               CCM_CS2CDR_SAI2_CLK_PRED(kSai2Pred - 1) |
               CCM_CS2CDR_SAI2_CLK_PODF(kSai2Podf - 1);

  // MCLK direction must be "output" for the SAI to clock itself from the CCM
  // root, but we deliberately never mux SAI2_MCLK onto a pad: that pad is
  // Teensy pin 33 = HP_ENABLE on this board.
  IOMUXC_GPR_GPR1 = (IOMUXC_GPR_GPR1 & ~IOMUXC_GPR_GPR1_SAI2_MCLK3_SEL_MASK) |
                    IOMUXC_GPR_GPR1_SAI2_MCLK_DIR |
                    IOMUXC_GPR_GPR1_SAI2_MCLK3_SEL(0);

  CORE_PIN4_CONFIG = 2;  // EMC_06, SAI2_TX_BCLK
  CORE_PIN3_CONFIG = 2;  // EMC_05, SAI2_TX_SYNC (LRCLK)
  CORE_PIN2_CONFIG = 2;  // EMC_04, SAI2_TX_DATA
  // CORE_PIN33_CONFIG intentionally NOT set -- see header.

  I2S2_TMR  = 0;
  I2S2_TCR1 = I2S_TCR1_TFW(4);
  I2S2_TCR2 = I2S_TCR2_SYNC(0) | I2S_TCR2_BCP | I2S_TCR2_BCD |
              I2S_TCR2_DIV(kSai2BclkDiv) | I2S_TCR2_MSEL(1);
  I2S2_TCR3 = I2S_TCR3_TCE;
  I2S2_TCR4 = I2S_TCR4_FRSZ(2 - 1) | I2S_TCR4_SYWD(32 - 1) | I2S_TCR4_MF |
              I2S_TCR4_FSD | I2S_TCR4_FSE | I2S_TCR4_FSP;
  I2S2_TCR5 = I2S_TCR5_WNW(32 - 1) | I2S_TCR5_W0W(32 - 1) | I2S_TCR5_FBT(32 - 1);
}

}  // namespace

// ===========================================================================
// SaiCapture
// ===========================================================================
SaiCapture* SaiCapture::instance_ = nullptr;

uint32_t SaiCapture::mclkHz()  { return kPllHz / (kSai1Pred * kSai1Podf); }
uint32_t SaiCapture::bclkHz()  { return mclkHz() / (2 * (kSai1BclkDiv + 1)); }
uint32_t SaiCapture::lrclkHz() { return bclkHz() / (kFrameWords * 32); }

void SaiCapture::resetStats() {
  blocks_ = 0; overruns_ = 0; max_isr_us_ = 0;
}

void SaiCapture::begin(CaptureCallback cb) {
  instance_ = this;
  cb_ = cb;
  resetStats();

  memset(g_rx_buffer, 0, sizeof(g_rx_buffer));
  arm_dcache_flush_delete(g_rx_buffer, sizeof(g_rx_buffer));

  g_rx_dma.begin(true);
  configSai1();

  I2S1_RCSR = 0;  // receiver off while the DMA is set up

#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
  // Read RDR0 and RDR1 alternately. SMOD(3) makes the source address wrap
  // inside an 8-byte window, which is exactly the two adjacent data registers
  // (SAI RDR0 is at offset 0xA0 in the peripheral, so it is 8-byte aligned).
  g_rx_dma.TCD->SADDR = (void*)&I2S1_RDR0;
  g_rx_dma.TCD->SOFF  = 4;
  g_rx_dma.TCD->ATTR  = DMA_TCD_ATTR_SSIZE(2) | DMA_TCD_ATTR_DSIZE(2) |
                        DMA_TCD_ATTR_SMOD(3);
  g_rx_dma.TCD->NBYTES_MLNO = 8;   // one 32-bit word from each data line
  g_rx_dma.TCD->SLAST = 0;         // SMOD already returns SADDR to RDR0
#else
  // Single data line: read RDR0 repeatedly.
  g_rx_dma.TCD->SADDR = (void*)&I2S1_RDR0;
  g_rx_dma.TCD->SOFF  = 0;
  g_rx_dma.TCD->ATTR  = DMA_TCD_ATTR_SSIZE(2) | DMA_TCD_ATTR_DSIZE(2);
  g_rx_dma.TCD->NBYTES_MLNO = 4;
  g_rx_dma.TCD->SLAST = 0;
#endif
  g_rx_dma.TCD->DADDR = g_rx_buffer;
  g_rx_dma.TCD->DOFF  = 4;
  const uint32_t minor_loops = sizeof(g_rx_buffer) / g_rx_dma.TCD->NBYTES_MLNO;
  g_rx_dma.TCD->CITER_ELINKNO = minor_loops;
  g_rx_dma.TCD->BITER_ELINKNO = minor_loops;
  g_rx_dma.TCD->DLASTSGA = -(int32_t)sizeof(g_rx_buffer);
  g_rx_dma.TCD->CSR = DMA_TCD_CSR_INTHALF | DMA_TCD_CSR_INTMAJOR;
  g_rx_dma.triggerAtHardwareEvent(DMAMUX_SOURCE_SAI1_RX);
  g_rx_dma.attachInterrupt(dmaIsr);
  NVIC_SET_PRIORITY(IRQ_DMA_CH0 + g_rx_dma.channel, kCapturePriority);
  g_rx_dma.enable();

  // FR clears the FIFO so the first frame we see is aligned to a frame sync.
  I2S1_RCSR = I2S_RCSR_RE | I2S_RCSR_BCE | I2S_RCSR_FRDE | I2S_RCSR_FR;
}

void SaiCapture::stop() {
  g_rx_dma.disable();
  I2S1_RCSR = 0;
  cb_ = nullptr;
}

void SaiCapture::dmaIsr() {
  const uint32_t t0 = ARM_DWT_CYCCNT;
  SaiCapture* self = instance_;
  uint32_t daddr = (uint32_t)(g_rx_dma.TCD->DADDR);
  g_rx_dma.clearInterrupt();

  // The half the DMA is NOT currently writing is the one that just filled.
  const uint32_t* src;
  if (daddr < (uint32_t)g_rx_buffer + sizeof(g_rx_buffer) / 2) {
    src = &g_rx_buffer[kRxWordsPerHalf];   // DMA in first half -> drain second
  } else {
    src = &g_rx_buffer[0];
  }
  arm_dcache_delete((void*)src, sizeof(g_rx_buffer) / 2);

#if QPR_CAPTURE_MODE == QPR_MODE_DUAL_I2S_192K
  // Buffer order per frame, set by the alternating RDR0/RDR1 reads:
  //   [0] RDR0 left  = ADC1 L = FLU
  //   [1] RDR1 left  = ADC2 L = BLD
  //   [2] RDR0 right = ADC1 R = FRD
  //   [3] RDR1 right = ADC2 R = BRU
  for (uint32_t i = 0; i < cfg::kDmaFramesPerHalf; i++) {
    const uint32_t* f = src + i * 4;
    g_frames[i].ch[cfg::CH_FLU] = slotToSample(f[0]);
    g_frames[i].ch[cfg::CH_BLD] = slotToSample(f[1]);
    g_frames[i].ch[cfg::CH_FRD] = slotToSample(f[2]);
    g_frames[i].ch[cfg::CH_BRU] = slotToSample(f[3]);
  }
#else
  // TDM slot order is ch1L, ch1R, ch2L, ch2R = FLU, FRD, BLD, BRU.
  for (uint32_t i = 0; i < cfg::kDmaFramesPerHalf; i++) {
    const uint32_t* f = src + i * 4;
    g_frames[i].ch[cfg::CH_FLU] = slotToSample(f[0]);
    g_frames[i].ch[cfg::CH_FRD] = slotToSample(f[1]);
    g_frames[i].ch[cfg::CH_BLD] = slotToSample(f[2]);
    g_frames[i].ch[cfg::CH_BRU] = slotToSample(f[3]);
  }
#endif

  if (self && self->cb_) self->cb_(g_frames, cfg::kDmaFramesPerHalf);
  if (self) {
    self->blocks_++;
    uint32_t us = (ARM_DWT_CYCCNT - t0) / (F_CPU_ACTUAL / 1000000u);
    if (us > self->max_isr_us_) self->max_isr_us_ = us;
  }
}

// ===========================================================================
// SaiMonitorOut
// ===========================================================================
SaiMonitorOut* SaiMonitorOut::instance_ = nullptr;

void SaiMonitorOut::begin(MonitorCallback cb) {
  instance_ = this;
  cb_ = cb;

  memset(g_tx_buffer, 0, sizeof(g_tx_buffer));
  arm_dcache_flush_delete(g_tx_buffer, sizeof(g_tx_buffer));
  for (uint32_t i = 0; i < kMonSlots; i++) g_mon_ready[i] = false;
  g_mon_read = g_mon_write = 0;

  g_tx_dma.begin(true);
  configSai2();

  I2S2_TCSR = 0;
  while (I2S2_TCSR & I2S_TCSR_TE) { }

  g_tx_dma.TCD->SADDR = g_tx_buffer;
  g_tx_dma.TCD->SOFF  = 4;
  g_tx_dma.TCD->ATTR  = DMA_TCD_ATTR_SSIZE(2) | DMA_TCD_ATTR_DSIZE(2);
  g_tx_dma.TCD->NBYTES_MLNO = 4;
  g_tx_dma.TCD->SLAST = -(int32_t)sizeof(g_tx_buffer);
  g_tx_dma.TCD->DADDR = (void*)&I2S2_TDR0;
  g_tx_dma.TCD->DOFF  = 0;
  g_tx_dma.TCD->CITER_ELINKNO = sizeof(g_tx_buffer) / 4;
  g_tx_dma.TCD->BITER_ELINKNO = sizeof(g_tx_buffer) / 4;
  g_tx_dma.TCD->DLASTSGA = 0;
  g_tx_dma.TCD->CSR = DMA_TCD_CSR_INTHALF | DMA_TCD_CSR_INTMAJOR;
  g_tx_dma.triggerAtHardwareEvent(DMAMUX_SOURCE_SAI2_TX);
  g_tx_dma.attachInterrupt(dmaIsr);
  NVIC_SET_PRIORITY(IRQ_DMA_CH0 + g_tx_dma.channel, kMonitorPriority);
  g_tx_dma.enable();

  // Low-priority software interrupt that runs the monitor DSP. It preempts
  // thread-level code (the SD writer) but is itself preempted by both audio
  // DMA interrupts, so the DSP can never delay capture.
  attachInterruptVector(IRQ_SOFTWARE, dspIsr);
  NVIC_SET_PRIORITY(IRQ_SOFTWARE, kDspPriority);
  NVIC_ENABLE_IRQ(IRQ_SOFTWARE);

  I2S2_TCSR = I2S_TCSR_TE | I2S_TCSR_BCE | I2S_TCSR_FRDE | I2S_TCSR_FR;
}

void SaiMonitorOut::stop() {
  g_tx_dma.disable();
  I2S2_TCSR = 0;
  NVIC_DISABLE_IRQ(IRQ_SOFTWARE);
  cb_ = nullptr;
}

void SaiMonitorOut::dspIsr() {
  SaiMonitorOut* self = SaiMonitorOut::instance_;
  if (!self || !self->cb_) return;

  // HARD CPU BUDGET. This interrupt sits at priority 208, which still
  // preempts thread mode -- and thread mode is where SD writing happens. On
  // ARMv7-M, pending an exception that is active-but-preempted causes it to be
  // re-taken on exit, so a render() that consistently overruns its period
  // would re-pend forever and hold loop() at zero CPU. The rings would fill in
  // about 128 ms and the take would be destroyed by a *monitoring* problem.
  //
  // So: stop rendering once this entry has spent kBudgetFraction of one block
  // period. An over-budget DSP glitches the monitor (the DAC interrupt already
  // emits silence on underrun) and never touches the recording.
  const uint32_t t0 = ARM_DWT_CYCCNT;
  const uint32_t period_cycles =
      (uint32_t)((uint64_t)F_CPU_ACTUAL * cfg::kMonitorBlockSamples /
                 cfg::kMonitorRateHz);
  const uint32_t budget = period_cycles / 2;   // 50% of one block period

  for (uint32_t guard = 0; guard < kMonSlots; guard++) {
    uint32_t w = g_mon_write;
    if (g_mon_ready[w]) return;                // ring full, nothing to do
    self->cb_(g_mon[w].left, g_mon[w].right, cfg::kMonitorBlockSamples);
    g_mon_ready[w] = true;
    g_mon_write = (w + 1) % kMonSlots;
    if ((ARM_DWT_CYCCNT - t0) >= budget) {
      self->over_budget_++;
      return;                                  // let the monitor underrun
    }
  }
}

void SaiMonitorOut::dmaIsr() {
  SaiMonitorOut* self = SaiMonitorOut::instance_;
  uint32_t saddr = (uint32_t)(g_tx_dma.TCD->SADDR);
  g_tx_dma.clearInterrupt();

  uint32_t* dest = (saddr < (uint32_t)g_tx_buffer + sizeof(g_tx_buffer) / 2)
                   ? &g_tx_buffer[kTxWordsPerHalf]   // DMA reading first half
                   : &g_tx_buffer[0];

  uint32_t r = g_mon_read;
  if (g_mon_ready[r]) {
    const float* l = g_mon[r].left;
    const float* rr = g_mon[r].right;
    for (uint32_t i = 0; i < kTxFramesPerHalf; i++) {
      dest[i * 2 + 0] = floatToSlot(l[i]);
      dest[i * 2 + 1] = floatToSlot(rr[i]);
    }
    g_mon_ready[r] = false;
    g_mon_read = (r + 1) % kMonSlots;
  } else {
    // No block ready: emit silence rather than repeating stale audio.
    memset(dest, 0, sizeof(g_tx_buffer) / 2);
    if (self) self->underruns_++;
  }
  arm_dcache_flush_delete(dest, sizeof(g_tx_buffer) / 2);

  // Ask the DSP for more. Pending is set from a higher-priority interrupt, so
  // the DSP runs as soon as the CPU drops below kDspPriority.
  NVIC_SET_PENDING(IRQ_SOFTWARE);
}

}  // namespace qpr
