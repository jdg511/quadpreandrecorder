import pcbnew, sys
b = pcbnew.LoadBoard(r"C:\Users\Jason\Documents\quadpreandrecorder\hardware\review_outputs\stackup_test.kicad_pcb")
ds = b.GetDesignSettings()
st = ds.GetStackupDescriptor()
print("type", type(st), [m for m in dir(st) if not m.startswith("_")][:60])
try:
    st.BuildDefaultStackupList(ds, 4)
    print("built; items:", len(list(st.GetList())))
    for it in st.GetList():
        print(" ", it.GetTypeName(), it.GetLayerName() if hasattr(it,'GetLayerName') else '', pcbnew.ToMM(it.GetThickness()) if hasattr(it,'GetThickness') else '')
except Exception as e:
    print("ERR", e)
print("m_HasStackup attr:", hasattr(ds, "m_HasStackup"))
