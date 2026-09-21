import sys, math
sys.argv = [sys.argv[0], "hardware/fabrication/drc-t10.json", "--dry", "--only", "__none__"]
sys.path.insert(0, "tools")
import astar_route as ar
import stitch_pass3 as sp
net, x0, y0, x1, y1 = "NAV_LEFT", 60.0, 10.0, 100.0, 76.0
sp.GND_NAMES = (net,); sp.CLEARANCE = 0.15
obs = sp.build_obstacles(ar.board)
o = ar.subset(obs, x0, y0, x1, y1)
G = 0.381
ox = 75.24 - round((75.24 - x0) / G) * G; oy = 62.5 - round((62.5 - y0) / G) * G
nx, ny = int((x1 - ox) / G) + 1, int((y1 - oy) / G) + 1
ar.GRID = G
free = ar.raster(o, x0, y0, nx, ny, ox, oy, 0.15, 0.0)
out = open("review_outputs/astar_debug.txt", "w")
for L, name in ((ar.F, "F"), (ar.B, "B")):
    out.write("layer %s origin %.3f %.3f  x from %.2f step %.3f\n" % (name, ox, oy, ox, G))
    for j in range(ny):
        out.write("%6.2f %s\n" % (oy + j * G, "".join("." if free[L][i][j] else "#" for i in range(nx))))
out.close()
