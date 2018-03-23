# sirepo_bluesky

Usage:
----
- make sure you have mongodb service running
- start ipython
- `%run -i re_config.py`
- `%run -i srw_detector.py`
- `RE(bp.grid_scan([srw_det], fs.xwidth, 0, 1e-3, 10, fs.ywidth, 0, 1e-3, 10, True))`
- get the data:
```py
hdr = db[-1]
imgs = list(hdr.data('srw_det_image'))
plt.imshow(imgs[31], aspect='equal')
```
