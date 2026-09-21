import sys, pcbnew
b = pcbnew.LoadBoard(r"C:\Users\Jason\Documents\quadpreandrecorder\hardware\QuadPreRecorder.kicad_pcb")
mm = pcbnew.ToMM
for ref in sys.argv[1:]:
    fp = b.FindFootprintByReference(ref)
    bb = fp.GetBoundingBox(False, False)
    cy = fp.GetCourtyard(fp.GetLayer()).BBox()
    print(f"{ref:5} pos ({mm(fp.GetPosition().x):.2f},{mm(fp.GetPosition().y):.2f}) bbox x {mm(bb.GetLeft()):.2f}..{mm(bb.GetRight()):.2f} y {mm(bb.GetTop()):.2f}..{mm(bb.GetBottom()):.2f} | courtyard x {mm(cy.GetLeft()):.2f}..{mm(cy.GetRight()):.2f} y {mm(cy.GetTop()):.2f}..{mm(cy.GetBottom()):.2f}")
