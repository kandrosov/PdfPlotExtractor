import json
import yaml

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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

  plt.xscale('log' if curves['axis_setup']['x']['log'] else 'linear')
  plt.yscale('log' if curves['axis_setup']['y']['log'] else 'linear')
  for idx, curve in enumerate(curves['curves']):
    if selected_indices and idx not in selected_indices: continue
    if selected_names and curve['name'] not in selected_names: continue
    print(f'{idx}: name={curve["name"]}, color={curve["stroking_color"]}')
    if 'y_up' not in curve:
      plt.plot(curve['x'], curve['y'], linewidth=curve['linewidth'], color=curve['stroking_color'])
    else:
      plt.fill_between(curve['x'], curve['y_up'], curve['y_down'], color=curve['stroking_color'])
  if len(curves['axis_setup']['x']['range']) == 2:
    plt.xlim(curves['axis_setup']['x']['range'])
  if len(curves['axis_setup']['y']['range']) == 2:
    plt.ylim(curves['axis_setup']['y']['range'])
  plt.savefig(args.out_pdf, bbox_inches='tight')
