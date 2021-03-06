#!/usr/bin/env python3
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.transforms as mpl_transforms
import matplotlib.ticker as mpl_ticker

from .config import Config, scatter_trials
from turbo.modules import UCB, EI, PI


def plot_overview(rec):
    """ a helper function to produce several useful plots at once"""
    # the objective and error plots are basically identical if the optimiser is
    # minimising so only plot both when minimising
    if rec.optimiser.is_maximising():
        plot_objective(rec)
    plot_error(rec, best_so_far=False)
    plot_error(rec, best_so_far=True)
    plot_timings(rec)
    plot_acquisition_value(rec)
    plot_acquisition_parameter(rec)
    plot_training_iterations(rec)


def plot_acquisition_parameter_function(parameter, start_trial, end_trial):
    """ A utility function to help determine the shape of the acquisition
    function parameter over time to help refine it.

    Args:
        parameter: the value or function for the acquisition function parameter
        start_trial (int): the trial number to start plotting at
        end_trial (int): the trial number to start plotting at
    """
    parameter = parameter if callable(parameter) else lambda trial_num: parameter
    func = lambda trial_num: 0 if trial_num < start_trial else parameter(trial_num)
    xs = np.linspace(0, end_trial, num=200)
    ys = [func(x) for x in xs]
    x_discrete = list(range(start_trial, end_trial+1))
    y_discrete = [func(x) for x in x_discrete]

    plt.title('Acquisition Parameter Value')
    plt.plot(xs, ys, label='acquisition value')
    plt.scatter(x_discrete, y_discrete, s=20)

    plt.xlabel('trial num')
    plt.ylabel('acquisition parameter')

    _set_trial_ticks(plt.gca(), end_trial)
    plt.show()


def _acquisition_parameter_name(acq_factory):
    if isinstance(acq_factory, UCB):
        return 'beta'
    elif isinstance(acq_factory, PI):
        return 'xi'
    elif isinstance(acq_factory, EI):
        return 'xi'
    else:
        raise NotImplementedError()


def plot_acquisition_parameter(rec, fig_ax=None):
    assert not rec.has_unfinished_trials()
    fig, ax = fig_ax if fig_ax is not None else plt.subplots(figsize=Config.fig_sizes['overview'])

    trials = rec.get_sorted_trials()
    assert trials, 'no trials'
    xs = [n for n, t in trials]
    name = _acquisition_parameter_name(rec.optimiser.acquisition)
    acq_params = [t.selection_info.get('acq_info', {}).get(name, 0) for n, t in trials]
    colors = [Config.trial_marker_colors[t.selection_info['type']] for n, t in trials]

    ax.margins(0.01, 0.05)
    ax.plot(xs, acq_params, label='acquisition parameter value')
    scatter_trials(ax, rec, xs, acq_params, trials)

    ax.set_title('Acquisition Parameter For Each Trial', fontsize=14)
    ax.set_xlabel('trial num')
    ax.set_ylabel('acquisition parameter value')

    _set_trial_ticks(ax, len(trials))
    ax.legend()
    return fig


def plot_acquisition_value(rec, fig_ax=None):
    assert not rec.has_unfinished_trials()
    fig, ax = fig_ax if fig_ax is not None else plt.subplots(figsize=Config.fig_sizes['overview'])

    trials = rec.get_sorted_trials()
    assert trials, 'no trials'
    xs = [n for n, t in trials]
    acq = [t.selection_info.get('maximisation_info', {}).get('max_acq', 0) for n, t in trials]
    colors = [Config.trial_marker_colors[t.selection_info['type']] for n, t in trials]

    ax.margins(0.01, 0.05)
    ax.plot(xs, acq, label='acquisition value')
    scatter_trials(ax, rec, xs, acq, trials)

    ax.set_title('Acquisition Function Value For Each Trial', fontsize=14)
    ax.set_xlabel('trial num')
    ax.set_ylabel('acquisition value')

    _set_trial_ticks(ax, len(trials))
    ax.legend()
    return fig

def plot_training_iterations(rec, fig_ax=None):
    assert not rec.has_unfinished_trials()
    fig, ax = fig_ax if fig_ax is not None else plt.subplots(figsize=Config.fig_sizes['overview'])

    trials = rec.get_sorted_trials()
    assert trials, 'no trials'
    xs = [n for n, t in trials]
    fitting_infos = [t.selection_info.get('fitting_info') for n, t in trials] # None if missing
    iterations = [0 if fi is None else fi['iterations'] for fi in fitting_infos]
    colors = [Config.trial_marker_colors[t.selection_info['type']] for n, t in trials]

    ax.margins(0.01, 0.05)
    ax.bar(xs, iterations, color=colors)

    ax.set_title('Surrogate Training Iterations For Each Trial', fontsize=14)
    ax.set_xlabel('trial num')
    ax.set_ylabel('iterations')

    _set_trial_ticks(ax, len(trials))
    return fig


def plot_timings(rec, show_selection=True, show_eval=True, show_total=True, ylim=None, fig_ax=None):
    """plot a line graph showing the selection and evaluation times of each trial

    Args:
        rec (Recorder): the recorder which observed the run of an optimiser
        ylim: when specified, set the limits of the y axis to
            get a better detailed look at that range of values (optional)
        fig_ax: the figure and axes to plot to in a tuple (optional)
    """
    assert not rec.has_unfinished_trials()
    fig, ax = fig_ax if fig_ax is not None else plt.subplots(figsize=Config.fig_sizes['overview'])
    assert show_selection or show_eval or show_total, 'have to show something'

    trials = rec.get_sorted_trials()
    assert trials, 'no trials'
    xs = [n for n, t in trials]
    selection_ys = [t.selection_time for n, t in trials]
    eval_ys = [t.eval_time for n, t in trials]
    total_ys = [s + e for s, e in zip(selection_ys, eval_ys)]

    ax.margins(0.01, 0.05)
    if show_selection:
        ax.plot(xs, selection_ys, label='selection time')
        scatter_trials(ax, rec, xs, selection_ys, trials)
    if show_eval:
        ax.plot(xs, eval_ys, label='evaluation time')
        scatter_trials(ax, rec, xs, eval_ys, trials)
    if show_total:
        ax.plot(xs, total_ys, '--', label='total time', linewidth=1)
        scatter_trials(ax, rec, xs, total_ys, trials)

    ax.set_title('Selection/Evaluation Time For Each Trial', fontsize=14)
    ax.set_xlabel('trial num')
    ax.set_ylabel('time (seconds)')

    if ylim is not None:
        ax.set_ylim(ylim)

    _set_trial_ticks(ax, len(trials))
    ax.legend()
    return fig


def plot_objective(rec, log_scale=False, ylim=None, fig_ax=None):
    """plot a line graph showing the value of the objective function for each trial

    Args:
        rec (Recorder): the recorder which observed the run of an optimiser
        log_scale: whether to plot on a logarithmic or a linear scale
        ylim: when specified, set the limits of the y/cost axis to
            get a better detailed look at that range of values (optional)
        fig_ax: the figure and axes to plot to in a tuple (optional)
    """
    assert not rec.has_unfinished_trials()
    fig, ax = fig_ax if fig_ax is not None else plt.subplots(figsize=Config.fig_sizes['overview'])

    trials = rec.get_sorted_trials()
    assert trials, 'no trials'
    _, incumbent = rec.get_incumbent()
    xs = [n for n, t in trials]
    ys = [t.y for n, t in trials]

    ax.margins(0.01, 0.05)
    ax.axhline(y=incumbent.y, linestyle='--', color='grey', linewidth=0.8)
    ax.plot(xs, ys, color='#4c72b0', label='objective value')
    scatter_trials(ax, rec, xs, ys, trials)

    ax.set_title('Objective Function Value For Each Trial', fontsize=14)
    ax.set_xlabel('trial num')
    ax.set_ylabel('objective value')

    if log_scale:
        ax.set_yscale('log')
    if ylim is not None:
        ax.set_ylim(ylim)

    _set_trial_ticks(ax, len(trials))
    ax.legend()
    return fig


def compare_error(recs, names=None, colors=None, true_best=None, log_scale=False, plot_best=False, best_so_far=False, ylim=None, fig_ax=None):
    """ plot a line graph showing the difference between the known optimal value
    and the optimiser's best guess for each trial of each of the recorders.

    Args:
        recs ([Recorder]): the recorders to compare
        names ([str]): human readable names for the recorders
        colors ([str]): custom colors for the recorders
        true_best (float): the globally optimal value to compare to. If not provided: the incumbent is used
        log_scale: whether to plot on a logarithmic or a linear scale
        plot_best: whether to plot a marker showing the trial with the overall best cost
        best_so_far: whether to plot the error for each trial, or the best error up until and including that trial
        ylim: when specified, set the limits of the y/cost axis to
            get a better detailed look at that range of values (optional)
        fig_ax: the figure and axes to plot to in a tuple (optional)
    """
    assert not any(rec.has_unfinished_trials() for rec in recs)
    maximising = recs[0].optimiser.is_maximising()
    assert all(rec.optimiser.is_maximising() == maximising for rec in recs), \
        'some optimisers are maximising, others minimising'
    fig, ax = fig_ax if fig_ax is not None else plt.subplots(figsize=Config.fig_sizes['overview'])
    if true_best is None:
        incumbents = [rec.get_incumbent()[1].y for rec in recs]
        true_best = np.max(incumbents) if maximising else np.min(incumbents)
    if colors is None:
        colors = [None] * len(recs)
    if names is None:
        names = ['run {}'.format(i+1) for i in range(len(recs))]

    if plot_best:
        ax.margins(0.01, 0.1)  # need more margins to fit the marker in
    else:
        ax.margins(0.01, 0.05)
    ax.axhline(y=0, linestyle='--', color='grey', linewidth=0.8)
    ax.set_title('Best Error Until Each Trial' if best_so_far else 'Error For Each Trial', fontsize=14)
    ax.set_xlabel('trial num')
    ax.set_ylabel('error')

    if log_scale:
        ax.set_yscale('log')
    if ylim is not None:
        ax.set_ylim(ylim)

    for i, rec in enumerate(recs):
        trials = rec.get_sorted_trials()
        assert trials, 'no trials'
        xs = [n for n, t in trials]
        errors = [(true_best - t.y if rec.optimiser.is_maximising() else t.y - true_best) for n, t in trials]

        # not efficient, but it works
        if best_so_far:
            errors = [np.min(errors[:i+1]) for i in range(len(errors))]

        if any(e < 0 for e in errors):
            print('warning: some of the trials are better than true_best!')

        ax.plot(xs, errors, color=colors[i], label=names[i])
        scatter_trials(ax, rec, xs, errors, trials)

        if plot_best:
            best_i = int(np.argmin(errors))

            # move the marker out of the way.
            offset = -4.5  # pt
            offset = mpl_transforms.ScaledTranslation(0, offset/fig.dpi, fig.dpi_scale_trans)
            trans = ax.transData + offset

            ax.plot(xs[best_i], errors[best_i], marker='^', color='#55a868',
                    linestyle='', markersize=10, zorder=10, markeredgecolor='black',
                    markeredgewidth=1, transform=trans)

    _set_trial_ticks(ax, np.max([len(rec.trials) for rec in recs]))
    ax.legend()
    return fig



def plot_error(rec, true_best=None, log_scale=False, plot_best=False, best_so_far=False, ylim=None, fig_ax=None):
    """ plot a line graph showing the difference between the known optimal value
    and the optimiser's best guess for each trial.

    Args:
        rec (Recorder): the recorder which observed the run of an optimiser
        true_best (float): the globally optimal value to compare to. If not provided: the incumbent is used
        log_scale: whether to plot on a logarithmic or a linear scale
        plot_best: whether to plot a marker showing the trial with the overall best cost
        best_so_far: whether to plot the error for each trial, or the best error up until and including that trial
        ylim: when specified, set the limits of the y/cost axis to
            get a better detailed look at that range of values (optional)
        fig_ax: the figure and axes to plot to in a tuple (optional)
    """
    assert not rec.has_unfinished_trials()
    fig, ax = fig_ax if fig_ax is not None else plt.subplots(figsize=Config.fig_sizes['overview'])

    trials = rec.get_sorted_trials()
    assert trials, 'no trials'
    if true_best is None:
        _, incumbent = rec.get_incumbent()
        true_best = incumbent.y
    xs = [n for n, t in trials]
    errors = [(true_best - t.y if rec.optimiser.is_maximising() else t.y - true_best)
              for n, t in trials]

    # not efficient, but it works
    if best_so_far:
        errors = [np.min(errors[:i+1]) for i in range(len(errors))]

    if any(e < 0 for e in errors):
        print('warning: some of the trials are better than true_best!')

    ax.margins(0.01, 0.05)
    ax.axhline(y=0, linestyle='--', color='grey', linewidth=0.8)
    ax.plot(xs, errors, color='#4c72b0', label='error')
    scatter_trials(ax, rec, xs, errors, trials)

    if plot_best:
        best_i = int(np.argmin(errors))

        # move the marker out of the way.
        offset = -4.5  # pt
        offset = mpl_transforms.ScaledTranslation(0, offset/fig.dpi, fig.dpi_scale_trans)
        trans = ax.transData + offset

        ax.plot(xs[best_i], errors[best_i], marker='^', color='#55a868',
                linestyle='', markersize=10, zorder=10, markeredgecolor='black',
                markeredgewidth=1, label='best cost', transform=trans)
        ax.margins(0.01, 0.1)  # need more margins to fit the marker in

    ax.set_title('Best Error Until Each Trial' if best_so_far else 'Error For Each Trial', fontsize=14)
    ax.set_xlabel('trial num')
    ax.set_ylabel('error')

    if log_scale:
        ax.set_yscale('log')
    if ylim is not None:
        ax.set_ylim(ylim)

    _set_trial_ticks(ax, len(trials))
    ax.legend()
    return fig


def _set_trial_ticks(ax, num_trials):
    if num_trials < 50:
        ax.xaxis.set_major_locator(mpl_ticker.MultipleLocator(2.0))
    elif num_trials < 100:
        ax.xaxis.set_major_locator(mpl_ticker.MultipleLocator(5.0))


