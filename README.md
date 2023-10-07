# PdfPlotExtractor
Extract plots from pdf into json or yaml format.

## Usage
1. Create calibration file
   ```shell
   python pdf_plot_extractor.py --calib calib.yaml plot.pdf
   ```
   If successful, two files will be created: `calib.yaml` and `calib.yaml.pdf`.
1. Specify location of at least two points in plot coordinate system for x and y in the calibration yaml produced in
the previous step.
If more than two points are provided, the first two will be used to transform the plot.
You can use `calib.yaml.pdf` to help you identify the points.
1. Extract plot
   ```shell
   python pdf_plot_extractor.py --calib calib.yaml --json plot.json --yaml plot.yaml --out-pdf plot_extracted.pdf plot.pdf
   ```
