import copy
import json
import math
import os
import pdfplumber
import sys
import yaml

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def find_ticks(lines, direction, max_length):
  tick_candidates = {}
  other_dir = 'y' if direction == 'x' else 'x'
  for line in lines:
    if line[f'{direction}0'] != line[f'{direction}1']: continue
    start = line[f'{other_dir}0']
    stop = line[f'{other_dir}1']
    #if stop - start > max_length: continue
    pos = start
    if pos not in tick_candidates:
      tick_candidates[pos] = []
    tick_candidates[pos].append(line)
  ticks = None
  for pos, lines in tick_candidates.items():
    if ticks is None or len(lines) > len(ticks) or (len(lines) == len(ticks) and pos < ticks[0][f'{other_dir}0']):
      ticks = lines
  ticks = sorted(ticks, key=lambda line: line[f'{direction}0'] )
  unique_ticks = []
  for tick in ticks:
    start = tick[f'{other_dir}0']
    stop = tick[f'{other_dir}1']
    if stop - start < max_length and (len(unique_ticks) == 0 or tick[f'{direction}0'] != unique_ticks[-1][f'{direction}0']):
      unique_ticks.append(tick)
  limits = None
  if len(ticks) >= 2:
    limits = [ ticks[0], ticks[-1] ]
  return unique_ticks, limits

def create_calib(page, calib_file, max_rel_tick_length):
  page_h, page_w = page['height'], page['width']
  ticks = {
    'x': find_ticks(page['lines'], 'x', page_h * max_rel_tick_length),
    'y': find_ticks(page['lines'], 'y', page_w * max_rel_tick_length)
  }

  calib_data = {
    'x': {
      'log': False,
      'dir': 'x',
      'ticks': [],
      'range': [],
    },
    'y': {
      'log': False,
      'dir': 'y',
      'ticks': [],
      'range': [],
    }
  }

  for direction, (tick_lines, limit_lines) in ticks.items():
    for idx, tick_line in enumerate(tick_lines):
      tick = {
        'index': idx,
        'page_coord': tick_line[direction + '0'],
        'plot_coord': None,
      }
      calib_data[direction]['ticks'].append(tick)

      x = []
      y = []
      for px, py in tick_line['pts']:
        x.append(px)
        y.append(page_h-py)
      plt.plot(x, y, color=tick_line['stroking_color'])

    if limit_lines:
      for limit_line in limit_lines:
        calib_data[direction]['range'].append(limit_line[direction + '0'])

  for char in page['chars']:
    plt.text(char['x0'], char['y0'], char['text'], fontsize=char['size'])

  with open(calib_file, 'w') as f:
    yaml.dump(calib_data, f)
  plt.axis('off')
  plt.savefig(calib_file + ".pdf", bbox_inches='tight')

def find_ref_ticks(calib_data):
  for direction in ['x', 'y']:
    calib_data[direction]['ref_ticks'] = []
    ticks = calib_data[direction]['ticks']
    for tick in ticks:
      if tick['plot_coord']:
        calib_data[direction]['ref_ticks'].append(tick)
        if len(calib_data[direction]['ref_ticks']) == 2:
          break
    if len(calib_data[direction]['ref_ticks']) != 2:
      raise RuntimeError(f"Could not find reference ticks for direction {direction}." +
                          " Please check the calibration data.")
  return calib_data

def define_scale_params(calib_data):
  for direction, data in calib_data.items():
    x = []
    y = []
    for tick in data['ref_ticks']:
      x_page = float(tick['page_coord'])
      x_plot = float(tick['plot_coord'])
      if data['log']:
        x_plot = math.log10(x_plot)
      x.append(x_page)
      y.append(x_plot)
    data['a'] = (y[1] - y[0]) / (x[1] - x[0])
    data['b'] = y[0] - data['a'] * x[0]

def transform(pos_page, a, b, log=False):
  y = a * pos_page + b
  if log:
    y = 10 ** y
  return y

def round_sig(x, n_sig_digits):
  round_digits = n_sig_digits - int(math.floor(math.log10(abs(x)))) - 1
  return round(x, round_digits)

def extract_curves(page, calib_data, n_sig_digits, min_n_points):
  define_scale_params(calib_data)
  page_h = page['height']

  axis_setup = {}
  for direction in [ 'x', 'y' ]:
    axis_setup[direction] = {
      'log': calib_data[direction]['log'],
      'range': []
    }
    calib = calib_data[direction]
    for page_coord in calib['range']:
      plot_coord = transform(page_coord, calib['a'], calib['b'], calib['log'])
      plot_coord = round_sig(plot_coord, n_sig_digits)
      axis_setup[direction]['range'].append(plot_coord)

  curves = []
  for idx, pdf_curve in enumerate(page['curves']):
    curve = { 'name': f'curve_{idx}' }
    for param in [ 'linewidth', 'stroke', 'fill', 'stroking_color', 'non_stroking_color' ]:
      curve[param] = pdf_curve[param]
    curve['x'] = []
    curve['y'] = []
    for point in pdf_curve['pts']:
      point = (point[0], page_h - point[1])
      for idx, direction in enumerate([ 'x', 'y' ]):
        calib = calib_data[direction]
        plot_coord = transform(point[idx], calib['a'], calib['b'], calib['log'])
        plot_coord = round_sig(plot_coord, n_sig_digits)
        curve[direction].append(plot_coord)
    has_up_down = False
    if curve['fill']:
      curve_up_down = copy.deepcopy(curve)
      curve_up_down['x'] = []
      del curve_up_down['y']
      curve_up_down['y_up'] = []
      curve_up_down['y_down'] = []
      low_idx = 0
      high_idx = len(curve['y']) - 1
      up_low = curve['y'][low_idx] > curve['y'][high_idx]
      all_ok = True
      while low_idx <= high_idx:
        x = curve['x'][low_idx]
        if x != curve['x'][high_idx]:
          all_ok = False
          print(f"Unable to extract up/down curves. X coordinates are not the same {x} != {curve['x'][high_idx]}.")
          print('curve x:', curve['x'])
          print('curve y:', curve['y'])
          break
        curve_up_down['x'].append(x)
        y_up = curve['y'][low_idx]
        y_down = curve['y'][high_idx]
        if up_low:
          y_up, y_down = y_down, y_up
        curve_up_down['y_up'].append(y_up)
        curve_up_down['y_down'].append(y_down)
        low_idx += 1
        high_idx -= 1
      if all_ok:
        curves.append(curve_up_down)
        has_up_down = True
    if not has_up_down:
      curves.append(curve)
  selected_curves = []
  for curve in curves:
    if not min_n_points or len(curve['x']) >= min_n_points:
      selected_curves.append(curve)
  result = {
    'axis_setup': axis_setup,
    'curves': selected_curves,
  }
  return result

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Extract plots from pdf.')
  parser.add_argument('--calib', required=True, type=str,
                      help="File with axis cailbration data. If file does not exist, it will be created.")
  parser.add_argument('--yaml', required=False, type=str, default=None, help="output yaml file")
  parser.add_argument('--json', required=False, type=str, default=None, help="output json file")
  parser.add_argument('--out-pdf', required=False, type=str, default=None,
                      help="output pdf file produced from the extracted data (to check the result)")
  parser.add_argument('--page', required=False, type=int, default=0, help="page number")
  parser.add_argument('--n-sig-digits', required=False, type=int, default=5, help="number of significant digits")
  parser.add_argument('--min-n-points', required=False, type=int, default=None,
                      help="minimal number of points in a curve")
  parser.add_argument('input_pdf', type=str, nargs=1, help="Input pdf file with the plot")
  args = parser.parse_args()

  pdf = pdfplumber.open(args.input_pdf[0])
  data = json.loads(pdf.to_json())
  page = data['pages'][args.page]
  if not os.path.exists(args.calib):
    create_calib(page, args.calib, 0.2)
    print(f'Created calibration file "{args.calib}". Please fill in the calibration data and run again.')
    sys.exit(0)
  print(f'Loading calibration data from {args.calib}')
  with open(args.calib, 'r') as f:
    calib_data = yaml.safe_load(f)
  calib_data = find_ref_ticks(calib_data)

  curves = extract_curves(page, calib_data, args.n_sig_digits, args.min_n_points)

  if args.yaml:
    with(open(args.yaml, 'w')) as f:
      yaml.dump(curves, f, default_flow_style=None, width=100)

  if args.json:
    with(open(args.json, 'w')) as f:
      json.dump(curves, f)

  if args.out_pdf:
    plt.xscale('log' if calib_data['x']['log'] else 'linear')
    plt.yscale('log' if calib_data['y']['log'] else 'linear')
    for curve in curves['curves']:
      if 'y_up' not in curve:
        plt.plot(curve['x'], curve['y'], linewidth=curve['linewidth'], color=curve['stroking_color'])
      else:
        plt.fill_between(curve['x'], curve['y_up'], curve['y_down'], color=curve['stroking_color'])
    if len(curves['axis_setup']['x']['range']) == 2:
      plt.xlim(curves['axis_setup']['x']['range'])
    if len(curves['axis_setup']['y']['range']) == 2:
      plt.ylim(curves['axis_setup']['y']['range'])
    plt.savefig(args.out_pdf, bbox_inches='tight')