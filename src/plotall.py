#!/usr/bin/env python3
"""Plot the results from lattice-sir.py
"""

import argparse
import logging
import os
from os.path import join as pjoin
from logging import debug, info

import datetime
import numpy as np
import pandas as pd
import scipy
import scipy.stats

import plotly
import plotly.graph_objects as go
from ipywidgets import widgets
import plotly.express as px

def plot_areai(indir):
    """Plot results from lattice-sir.py

    Args:
    indir(str): path to the parent directory of the results
    """
    df = pd.read_csv(pjoin(indir, 'exps.csv'))
    areai = []

    for expidx in df.expidx:
        aux = pd.read_csv(pjoin(indir, expidx, 'sir.csv'))
        areai.append(np.sum(aux.I))

    df['areai'] = areai
    gradstds = df['gradstd'].unique()
    areai = np.ndarray((len(gradstds), 2))

     # = np.ndarray((len(gradstds), 2))

    for i, g in enumerate(gradstds):
        rows = df.loc[df['gradstd'] == g]
        mymean = np.mean(rows['areai'])
        mystd = np.std(rows['areai'])
        areai[i][0] = mymean
        areai[i][1] = mystd

    dataareai = go.Scatter(
        x=gradstds,
        y=areai[:, 0],
        line=dict(width=4),
        name='Area under the curve of I',
        error_y=dict(
            type='data', # value of error bar given in data coordinates
            array=areai[:, 1],
            visible=True)
    )
    plotdata = [dataareai]
    plotlayout = go.Layout(
        title='Elapsed time to stationary state',
        xaxis=dict(
            title='Uniformity of the gradients (std of the gaussian)'
        ),
        yaxis=dict(
            title='Time (t)'
        )
    )

    fig = go.Figure(
        data=plotdata,
        layout=plotlayout
    )
    fig.show()

def plot_areai(indir):
    """Plot results from lattice-sir.py

    Args:
    indir(str): path to the parent directory of the results
    """
    df = pd.read_csv(pjoin(indir, 'exps.csv'))
    areai = []

    for expidx in df.expidx:
        aux = pd.read_csv(pjoin(indir, expidx, 'sir.csv'))
        areai.append(np.sum(aux.I))

    df['areai'] = areai
    gradstds = df['gradstd'].unique()
    areai = np.ndarray((len(gradstds), 2))

     # = np.ndarray((len(gradstds), 2))

    for i, g in enumerate(gradstds):
        rows = df.loc[df['gradstd'] == g]
        mymean = np.mean(rows['areai'])
        mystd = np.std(rows['areai'])
        areai[i][0] = mymean
        areai[i][1] = mystd

    dataareai = go.Scatter(
        x=gradstds,
        y=areai[:, 0],
        line=dict(width=4),
        name='Recovered rate vs uniformity of the gradients',
        error_y=dict(
            type='data', # value of error bar given in data coordinates
            array=areai[:, 1],
            visible=True)
    )
    plotdata = [dataareai]
    plotlayout = go.Layout(
        title='Elapsed time to stationary state',
        xaxis=dict(
            title='Uniformity of the gradients (std of the gaussian)'
        ),
        yaxis=dict(
            title='Infection time (area under the curve of I)'
        )
    )

    fig = go.Figure(
        data=plotdata,
        layout=plotlayout
    )
    fig.show()
def plot_all(indir):
    """Plot results from lattice-sir.py

    Args:
    indir(str): path to the parent directory of the results
    """
    df = pd.read_csv(pjoin(indir, 'exps.csv'))
    modes = []
    argmins = []
    areai = []
    for expidx in df.expidx:
        aux = pd.read_csv(pjoin(indir, expidx, 'sir.csv'))

        mymode = np.argmax(aux.I)
        modes.append(int(mymode))

        myargmin = np.argmin(aux.S)
        argmins.append(int(myargmin))
        areai.append(np.sum(aux.I))

    df['mode_i'] = modes
    df['argmin_s'] = argmins
    df['area_i'] = areai
    gradstds = df['gradstd'].unique()

    modei = np.ndarray((len(gradstds), 2))
    argmins = np.ndarray((len(gradstds), 2))

    for i, g in enumerate(gradstds):
        rows = df.loc[df['gradstd'] == g]

        mymean = np.mean(rows['mode_i'])
        mystd = np.std(rows['mode_i'])
        modei[i][0] = mymean
        modei[i][1] = mystd

        mymean = np.mean(rows['argmin_s'])
        mystd = np.std(rows['argmin_s'])
        argmins[i][0] = mymean
        argmins[i][1] = mystd

    datamode = go.Scatter(
        x=gradstds,
        y=modei[:, 0],
        name='Arg max of I',
        line=dict(width=4),
        error_y=dict(
            type='data', # value of error bar given in data coordinates
            array=modei[:, 1],
            visible=True)
    )
    dataargmin = go.Scatter(
        x=gradstds,
        y=argmins[:, 0],
        line=dict(width=4),
        name='Arg min of S',
        error_y=dict(
            type='data', # value of error bar given in data coordinates
            array=argmins[:, 1],
            visible=True)
    )
    plotdata = [datamode, dataargmin]
    plotlayout = go.Layout(
        title='Transmission time vs gradients uniformity',
        xaxis=dict(
            title='Uniformity (std of the gaussian)'
        ),
        yaxis=dict(
            title='Time'
        )
    )
    fig = go.Figure(
        data=plotdata,
        layout=plotlayout
    )
    fig.show()

def read_niterations(outdir):
    """Read number of iterations for in each folder in @outdir

    Args:
    outdir(str): results directory containing the subolders

    Returns:
    dict: folder names as keys and counts as values
    """

    counts = {}

    for expidx in os.listdir(outdir):
        if not os.path.isdir(pjoin(outdir, expidx)): continue
        summarypath = pjoin(outdir, expidx, 'sir.csv')
        counts[expidx] = sum(1 for line in open(summarypath))

    return counts

def get_inverse_map(mydict):
    return {v: k for k, v in mydict.items()}

def remap_to_categorical_data(df, cols):
    tickslabels = {}
    for col in cols:
        vals = sorted(df[col].unique())
        tickslabels[col] = vals
        aux = dict(enumerate(vals))
        aux = get_inverse_map(aux)
        df[col] = df[col].map(aux)
    return df, tickslabels

def plot_parallel_coordinates(expsdf, colslabels, categcols, tickslabels, outdir):

    dimensions = []
    for col in categcols: # categorical columns
        colname = colslabels[col]
        plotcol = dict(
            label = colname,
            values = expsdf[col],
            tickvals = list(range(len(tickslabels[col]))),
            ticktext = tickslabels[col])
        dimensions.append(plotcol)

    dimensions.append(
        dict(label = 'Convergence time',
             values = expsdf['t'],
    ))

    fig = go.Figure(data=go.Parcoords(
        line_color='blue',
        dimensions = dimensions
    )
                    )
    plotpath = pjoin(outdir, 'parallel.html')
    plotly.offline.plot(fig, filename=plotpath, auto_open=False)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resdir', nargs='+',
                        help='Directory(ies) containing the output from lattice-sir')
    args = parser.parse_args()

    logging.basicConfig(format='[%(asctime)s] %(message)s',
                        datefmt='%Y%m%d %H:%M', level=logging.DEBUG)

    outdir = '/tmp'

    # topologymap = {'erdos': 0, 'lattice': 1}
    topologynames = sorted(['erdos', 'lattice'])
    layoutnames = sorted(['grid', 'fr', 'kk'])
    erdosavgdegrnames = ['DotNotApply', '1', '4', '10', 'Fully']
    # layoutmap = {'fr': 0, 'grid': 1, 'kk': 2}

    dfs = []
    for i, resdir in enumerate(args.resdir):
        expspath = pjoin(resdir, 'exps.csv')
        df = pd.read_csv(expspath, index_col='expidx')
        niterations = read_niterations(resdir)
        niterations = pd.Series(niterations, index=df.index, dtype=int)
        df['t'] = niterations
        # df['topologymodel'] = df.topologymodel.map(topologymap)
        # df['layoutmodel'] = df.layoutmodel.map(layoutmap)
        dfs.append(df)

    df = pd.concat(dfs)
    colslabels = {'topologymodel': 'topology',
                'layoutmodel': 'spatiality',
                'erdosavgdegree': 'erdos-avgdegr',
                'latticethoroidal': 'lattice-thoroidal',
                'beta': 'beta',
                'gamma': 'gamma',
                'gaussianstds': 'gradients dispersion',
                't': 'convergence time',
                }
    df = df[colslabels.keys()]
    categcols = list(colslabels.keys())
    categcols.remove('t')
    expsdf, tickslabels = remap_to_categorical_data(df, categcols)
    plot_parallel_coordinates(expsdf, colslabels, categcols, tickslabels, outdir)

if __name__ == "__main__":
    main()
