'''
General Utilities for use with the optimiser library
'''

import sys
if sys.version_info[0] == 3: # python 3
    from math import isclose, inf
elif sys.version_info[0] == 2: # python 2
    inf = float('inf')
    def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
        ''' implementation from the python3 documentation '''
        return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
else:
    print('unsupported python version')

import json
import warnings
import numpy as np

# for serialising Gaussian Process models for saving to disk
import pickle
import base64
import zlib



class dotdict(dict):
    '''
        provide syntactic sugar for accessing dict elements with a dot eg
        mydict = {'somekey': 1}
        d = dotdict(mydict)
        d.somekey   # 1
        d.somekey = 2
        d.somekey   # 2
    '''
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError # have to convert to the correct exception
    def __setattr__(self, name, val):
        self[name] = val
    def copy(self):
        ''' copy.copy() does not work with dotdict '''
        return dotdict(dict.copy(self))

def set_str(set_):
    '''
    format a set as a string. The results of str.format are undesirable and inconsistent:

    python2:
    >>> '{}'.format(set([]))
    'set([])'
    >>> '{}'.format(set([1,2,3]))
    'set([1, 2, 3])'

    python3:
    >>> '{}'.format(set([]))
    'set()'
    >>> '{}'.format(set([1,2,3]))
    '{1, 2, 3}'

    set_str():
    >>> set_str(set([]))
    '{}'
    >>> set_str(set([1,2,3]))
    '{1, 2, 3}'

    '''
    return '{' + ', '.join([str(e) for e in set_]) + '}'

class NumpyJSONEncoder(json.JSONEncoder):
    ''' unfortunately numpy primitives are not JSON serialisable '''
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyJSONEncoder, self).default(obj)

def JSON_encode_binary(data):
    '''
    encode the given data in a compressed binary format, then encode that in
    base64 so that it can be stored compactly in a JSON string
    '''
    return base64.b64encode(zlib.compress(pickle.dumps(data))).decode('utf-8')
def JSON_decode_binary(data):
    ''' decode data encoded with JSON_encode_binary '''
    return pickle.loads(zlib.decompress(base64.b64decode(data)))

#TODO: make2D_col
def make2D(arr):
    ''' convert a numpy array with shape (l,) into an array with shape (l,1)
        (np.atleast_2d behaves similarly but would give shape (1,l) instead)
    '''
    return arr.reshape(-1, 1)
def make2D_row(arr):
    ''' convert a numpy array with shape (l,) into an array with shape (1,l)
    '''
    return arr.reshape(1, -1)

def logspace(from_, to, num_per_mag=1):
    '''
    num_per_mag: number of samples per order of magnitude
    '''
    from_exp = np.log10(from_)
    to_exp = np.log10(to)
    num = abs(to_exp-from_exp)*num_per_mag + 1
    return np.logspace(from_exp, to_exp, num=num, base=10)

def time_string(seconds):
    '''
    given a duration in the number of seconds (not necessarily an integer),
    format a string of the form: 'HH:MM:SS.X' where HH and X are present only
    when required.
    - HH is displayed if the duration exceeds 1 hour
    - X is displayed if the time does not round to an integer when truncated to
      1dp. eg durations ending in [.1, .9)
    '''
    mins, secs  = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    hours, mins = int(hours), int(mins)

    dps = 1 # decimal places to display
    # if the number of seconds would round to an integer: display it as one
    if isclose(round(secs), secs, abs_tol=10**(-dps)): # like abs_tol=1e-dps
        secs = '{:02d}'.format(int(round(secs)))
    else:
        # 0N => pad with leading zeros up to a total length of N characters
        #       (including the decimal point)
        # .Df => display D digits after the decimal point
        # eg for 2 digits before the decimal point and 1dp: '{:04.1f}'
        chars = 2+1+dps # (before decimal point)+1+(after decimal point)
        secs = ('{:0' + str(chars) +'.' + str(dps) + 'f}').format(secs)

    if hours > 0:
        return '{:02d}:{:02d}:{}'.format(hours, mins, secs)
    else:
        return '{:02d}:{}'.format(mins, secs)

def config_string(config, order=None, precise=False):
    '''
    similar to the string representation of a dictionary
    order: order of dictionary keys, None => alphabetical order
    precise: True => truncate numbers to a certain length. False => display all precision
    '''
    assert order is None or set(order) == set(config.keys())
    order = sorted(config.keys()) if order is None else order
    if len(order) == 0:
        return '{}'
    else:
        string = '{'
        for p in order:
            if isinstance(config[p], str) or isinstance(config[p], np.str_):
                string += '{}="{}", '.format(p, config[p])
            else: # assuming numeric
                if precise:
                    string += '{}={}, '.format(p, config[p])
                else:
                    # 2 significant figures
                    string += '{}={:.2g}, '.format(p, config[p])
        string = string[:-2] # remove trailing comma and space
        string += '}'
        return string

def exception_string():
    ''' get a string formatted with the last exception '''
    import traceback
    return ''.join(traceback.format_exception(*sys.exc_info()))

def is_numeric(obj):
    '''
    whether 'obj' is a numeric quantity, not including types which may be
    converted to a numeric quantity such as strings. Also numpy arrays are
    specifically excluded, however they do support +-*/ etc.

    Modified from: https://stackoverflow.com/a/500908
    '''
    if isinstance(obj, np.ndarray):
        return False

    if sys.version_info[0] == 3: # python 3
        attrs = ['__add__', '__sub__', '__mul__', '__truediv__', '__pow__']
    elif sys.version_info[0] == 2: # python 2
        attrs = ['__add__', '__sub__', '__mul__', '__div__', '__pow__']

    return all(hasattr(obj, attr) for attr in attrs)

class WarningCatcher(warnings.catch_warnings):
    '''
    capture any warnings raised within the with statement and instead of
    printing them, pass them to the given function. Example:
    with WarningCatcher(lambda warn: print(warn)):
        # stuff

    Note: it is possible to nest WarningCatchers, in which case the inner most
        catcher is the only one which receives the warning.
    Note: because of the nature of warnings, on_warning is only called when the
        with statement ends rather than immediately when the warning is raised
        (unlike exceptions).
    '''
    def __init__(self, on_warning):
        '''
        on_warning: a function which takes a warning and does something with it
        '''
        super(WarningCatcher, self).__init__(record=True)
        self.on_warning = on_warning
    def __enter__(self):
        self.warning_list = super(WarningCatcher, self).__enter__()
    def __exit__(self, *args):
        for warn in self.warning_list:
            self.on_warning(warn)
        super(WarningCatcher, self).__exit__(*args)


class RangeType:
    ''' The possible types of parameter ranges (see range_type() for details) '''
    Arbitrary   = 'arbitrary'
    Constant    = 'constant'
    Linear      = 'linear'
    Logarithmic = 'logarithmic'

def range_type(range_):
    ''' determine whether the range is arbitrary, constant, linear or logarithmic
    range_: must be numpy array

    Note: range_ must be sorted either ascending or descending to be detected as
        linear or logarithmic

    Range types:
        - Arbitrary: 0 or >1 element, not linear or logarithmic (perhaps not numeric)
                     Note: arrays of identical or nearly identical elements are
                     Arbitrary, not Constant
        - Constant: 1 element (perhaps not numeric)
        - Linear: >2 elements, constant non-zero difference between adjacent elements
        - Logarithmic: >2 elements, constant non-zero difference between adjacent log(elements)
    '''
    if len(range_) == 1:
        return RangeType.Constant
    # 'i' => integer, 'u' => unsigned integer, 'f' => floating point
    elif len(range_) < 2 or range_.dtype.kind not in 'iuf':
        return RangeType.Arbitrary
    else:
        # guaranteed: >2 elements, numeric

        # if every element is identical then it is Arbitrary. Not Constant
        # because constant ranges must have a single element.
        if np.all(np.isclose(range_[0], range_)):
            return RangeType.Arbitrary

        tmp = range_[1:] - range_[:-1] # differences between element i and element i+1
        # same non-zero difference between each element
        is_lin = np.all(np.isclose(tmp[0], tmp))
        if is_lin:
            return RangeType.Linear
        else:
            tmp = np.log(range_)
            tmp = tmp[1:] - tmp[:-1]
            is_log = np.all(np.isclose(tmp[0], tmp))
            if is_log:
                return RangeType.Logarithmic
            else:
                return RangeType.Arbitrary

def log_uniform(low, high, size=None):
    ''' sample a random number in the interval [low, high] distributed logarithmically within that space '''
    return np.exp(np.random.uniform(np.log(low), np.log(high), size=size))

def close_to_any(x, xs, tol=1e-5):
    ''' whether the point x is close to any of the points in xs
    x: the point to test. shape=(1, num_attribs)
    xs: the points to compare with. shape=(num_points, num_attribs)
    tol: maximum size of the squared Euclidean distance to be considered 'close'
    '''
    assert x.shape[1] == xs.shape[1], 'different number of attributes'
    assert x.shape[0] == 1, 'x must be a single point'
    assert xs.shape[0] > 0, 'xs must not be empty'
    assert len(x.shape) == len(xs.shape) == 2, 'must be 2D arrays'

    #return np.any(np.linalg.norm(xs - x, axis=1) <= tol)  # l2 norm (Euclidean distance)
    # x is subtracted from each row of xs, each element is squared, each row is
    # summed to leave a 1D array and each sum is checked with the tolerance
    return np.any(np.sum((xs - x)**2, axis=1) <= tol) # squared Euclidean distance

