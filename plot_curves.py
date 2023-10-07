import json
import yaml

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot_curves(curves, out_pdf, selected_indices=None, selected_names=None):
  pts_per_inch = 72.
  if 'page_setup' in curves:
    plt.figure(figsize=(curves['page_setup']['width']/pts_per_inch, curves['page_setup']['height']/pts_per_inch))
  plt.xscale('log' if curves['axis_setup']['x']['log'] else 'linear')
  plt.yscale('log' if curves['axis_setup']['y']['log'] else 'linear')
  for idx, curve in enumerate(curves['curves']):
    if selected_indices and idx not in selected_indices: continue
    if selected_names and curve['name'] not in selected_names: continue

    if 'y_up' not in curve:
      color = curve['stroking_color']
      plt.plot(curve['x'], curve['y'], linewidth=curve['linewidth'], color=color)
    else:
      color = curve['non_stroking_color']
      if not color:
        color = curve['stroking_color']
      plt.fill_between(curve['x'], curve['y_up'], curve['y_down'], color=color)
    print(f'{idx}: name={curve["name"]}, color={color}')
  if len(curves['axis_setup']['x']['range']) == 2:
    plt.xlim(curves['axis_setup']['x']['range'])
  if len(curves['axis_setup']['y']['range']) == 2:
    plt.ylim(curves['axis_setup']['y']['range'])
  plt.savefig(out_pdf, bbox_inches='tight')


if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Plot extracted curves.')
  parser.add_argument('--out-pdf', required=True, type=str, default=None,
                      help="output pdf file produced from the extracted data (to check the result)")
  parser.add_argument('--idx', required=False, type=str, default=None,
                      help="comma separated list of curve indices to plot")
  parser.add_argument('--name', required=False, type=str, default=None,
                      help="comma separated list of curve names to plot")
  parser.add_argument('input', type=str, nargs=1, help="input file in json or yaml format")
  args = parser.parse_args()

  input = args.input[0]
  with open(input, 'r') as f:
    if input.endswith('.json'):
      curves = json.load(f)
    else:
      curves = yaml.safe_load(f)

  selected_indices = None
  if args.idx:
    selected_indices = [int(idx) for idx in args.idx.split(',')]
  selected_names = None
  if args.name:
    selected_names = args.name.split(',')

  plot_curves(curves, args.out_pdf, selected_indices, selected_names)
