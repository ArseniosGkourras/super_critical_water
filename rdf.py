import numpy as np
import matplotlib.pyplot as plt

fname = "rdf_all.rdf"

blocks = []
current = None

with open(fname) as f:
    for line in f:
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) == 2:
            if current is not None:
                blocks.append(np.array(current, float))
            current = []
        else:
            current.append([float(x) for x in parts])

if current is not None:
    blocks.append(np.array(current, float))

# average g(r) across all blocks
g77_all = np.mean([b[:, 2] for b in blocks], axis=0)
g88_all = np.mean([b[:, 4] for b in blocks], axis=0)
g78_all = np.mean([b[:, 6] for b in blocks], axis=0)
r = blocks[0][:, 1]

plt.plot(r, g77_all, label="O-O")
plt.plot(r, g88_all, label="H-H")
plt.plot(r, g78_all, label="O-H")
plt.xlabel("r")
plt.ylabel("g(r)")
plt.legend()
plt.tight_layout()

# Save data to file for user
out = np.column_stack([r, g77_all, g88_all, g78_all])
np.savetxt("rdf_average.dat", out, header="r g77 g88 g78")

plt.show()
