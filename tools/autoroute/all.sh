#!/bin/bash
D=/sessions/keen-peaceful-brahmagupta/mnt/quadpreandrecorder/tools/autoroute
rm -f /tmp/ar_state.pkl
F=""
r(){ python3 -u $D/step.py "$1" "$2" "$3" "$4" || F="$F $1"; }
r HP_CPP       1.10 4.0 3000000
r HP_CPN       1.10 4.0 3000000
r HP_ENABLE    1.10 4.0 3000000
r ADC_LDO      1.10 4.0 3000000
r "+5V"        1.10 4.0 3000000
r "+3V3_A"     1.10 4.0 3000000
r "+3V3_D"     1.10 4.0 3000000
r ADC_MCLK_IC  1.10 4.0 3000000
r ADC_TDM      1.10 4.0 3000000
r ADC_BCLK_IC  1.15 4.0 2500000
r ADC_DOUT2_IC 1.15 4.0 2500000
r GAIN_B       1.20 4.0 2000000
r REC_BUTTON   1.25 4.0 2000000
r FLU_ADC      1.35 4.0 1500000
r BLD_PAD      1.45 4.0 1500000
r FRD_PAD      1.60 4.0 1200000
r FLU_PAD      1.60 4.0 1200000
r FLU_RAW      1.80 4.0 1000000
r PAD_DBG      1.80 4.0 1000000
echo "FAILED:$F"
