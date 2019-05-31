#AUTOGENERATED! DO NOT EDIT! File to edit: dev/01_core.ipynb (unless otherwise specified).

__all__ = ['newchk', 'patch', 'chk', 'tensor', 'ls', 'add_docs', 'docs', 'custom_dir', 'is_iter', 'coll_repr',
           'GetAttr', 'L', 'defaults', 'ifnone', 'noop', 'noops', 'tuplify', 'replicate', 'uniqueify', 'setify',
           'is_listy', 'range_of', 'mask2idxs', 'apply', 'to_detach', 'to_half', 'to_float', 'to_device', 'to_cpu',
           'item_find', 'find_device', 'find_bs', 'compose', 'mapper', 'partialler', 'add_props', 'make_cross_image',
           'opt_call', 'all_union', 'all_disjoint', 'camel2snake', 'trainable_params']

from .test import *
from .imports import *
from .notebook.showdoc import show_doc

def newchk(cls):
    "Class decorator to avoid recreating object passed to constructor"
    old_new,old_init  = cls.__new__,cls.__init__

    def _inner_new(cls, x=None, *args, **kwargs):
        if x is not None and isinstance(x,cls):
            x._newchk = 1
            return x
        res = old_new(cls)
        res._newchk = 0
        return res

    def _inner_init(self, *args, **kwargs):
        if self._newchk: return
        old_init(self, *args, **kwargs)

    cls.__new__  = functools.update_wrapper(_inner_new,  cls.__init__)
    cls.__init__ = functools.update_wrapper(_inner_init, cls.__init__)
    return cls

def patch(f):
    "Decorator: add `f` to the first parameter's class (based on f's type annotations)"
    cls = next(iter(f.__annotations__.values()))
    nf = copy.copy(f)
    functools.update_wrapper(nf,f)
    nf.__qualname__ = f"{cls.__name__}.{f.__name__}"
    setattr(cls, f.__name__, nf)
    return f

#NB: Please don't move this to a different line or module, since it's used in testing `get_source_link`
def chk(f): return typechecked(always=True)(f)

def tensor(x, *rest):
    "Like `torch.as_tensor`, but handle lists too, and can pass multiple vector elements directly."
    if len(rest): x = (x,)+rest
    # Pytorch bug in dataloader using num_workers>0
    if isinstance(x, (tuple,list)) and len(x)==0: return tensor(0)
    res = torch.tensor(x) if isinstance(x, (tuple,list)) else as_tensor(x)
    if res.dtype is torch.int32:
        warn('Tensor is int32: upgrading to int64; for better performance use int64 input')
        return res.long()
    return res

Tensor.ndim = property(lambda x: x.dim())

@patch
def ls(self:Path):
    "Contents of path as a list"
    return list(self.iterdir())

def add_docs(cls, **docs):
    "Copy values from `docs` to `cls` docstrings, and confirm all public methods are documented"
    for k,v in docs.items(): getattr(cls,k).__doc__ = v
    # List of public callables without docstring
    nodoc = [c for n,c in vars(cls).items() if isinstance(c,Callable)
             and not n.startswith('_') and c.__doc__ is None]
    assert not nodoc, f"Missing docs: {nodoc}"
    assert cls.__doc__ is not None, f"Missing class docs: {cls}"

def docs(cls):
    "Decorator version of `add_docs"
    add_docs(cls, **cls._docs)
    return cls

def custom_dir(c, add:List):
    "Implement custom `__dir__`, adding `add` to `cls`"
    return dir(type(c)) + list(c.__dict__.keys()) + add

def is_iter(o):
    "Test whether `o` can be used in a `for` loop"
    #Rank 0 tensors in PyTorch are not really iterable
    return isinstance(o, (Iterable,Generator)) and getattr(o,'ndim',1)

def coll_repr(c, max=1000):
    "String repr of up to `max` items of (possibly lazy) collection `c`"
    return f'(#{len(c)}) [' + ','.join(itertools.islice(map(str,c), 10)) + ('...'
            if len(c)>10 else '') + ']'

class GetAttr:
    "Inherit from this to have all attr accesses in `self._xtra` passed down to `self.default`"
    _xtra=[]
    def __getattr__(self,k):
        assert self._xtra, "Inherited from `GetAttr` but no `_xtra` attrs listed"
        if k in self._xtra: return getattr(self.default, k)
        raise AttributeError(k)
    def __dir__(self): return custom_dir(self, self._xtra)

def _mask2idxs(mask):
    mask = list(mask)
    if isinstance(mask[0],bool): return [i for i,m in enumerate(mask) if m]
    return [int(i) for i in mask]

def _listify(o):
    if o is None: return []
    if isinstance(o, list): return o
    if isinstance(o, (str,np.ndarray,Tensor)): return [o]
    if is_iter(o): return list(o)
    return [o]

@newchk
class L(GetAttr):
    "Behaves like a list of `items` but can also index with list of indices or masks"
    _xtra =  [o for o in dir(list) if not o.startswith('_')]

    def __init__(self, items=None, *rest, use_list=False, match=None):
        items = [] if items is None else items
        self.items = self.default = list(items) if use_list else _listify(items)
        self.items += list(rest)
        if match is not None:
            if len(self.items)==1: self.items = self.items*len(match)
            else: assert len(self.items)==len(match), 'Match length mismatch'

    def __len__(self): return len(self.items)
    def __delitem__(self, i): del(self.items[i])
    def __repr__(self): return f'{coll_repr(self)}'
    def __eq__(self,b): return all_equal(b,self)
    def __iter__(self): return (self[i] for i in range(len(self)))
    def __mul__ (a,b): return L(a.items*b)
    def __add__ (a,b): return L(a.items+_listify(b))
    def __radd__(a,b): return L(b)+a
    def __addi__(a,b):
        a.items += list(b)
        return a

    def __getitem__(self, idx):
        "Retrieve `idx` (can be list of indices, or mask, or int) items"
        res = [self.items[i] for i in _mask2idxs(idx)] if is_iter(idx) else self.items[idx]
        if isinstance(res,(tuple,list)) and not isinstance(res,L): res = L(res)
        return res

    def __setitem__(self, idx, o):
        "Set `idx` (can be list of indices, or mask, or int) items to `o` (which is broadcast if not iterable)"
        idx = idx if isinstance(idx,L) else _listify(idx)
        if not is_iter(o): o = [o]*len(idx)
        for i,o_ in zip(idx,o): self.items[i] = o_

    def sorted(self, key=None, reverse=False):
        "New `L` sorted by `key`. If key is str then use `attrgetter`. If key is int then use `itemgetter`."
        if isinstance(key,str):   k=lambda o:getattr(o,key,0)
        elif isinstance(key,int): k=itemgetter(key)
        else: k=key
        return L(sorted(self.items, key=k, reverse=reverse))

    def mapped(self, f):    return L(map(f, self))
    def zipped(self):       return L(zip(*self))
    def itemgot(self, idx): return self.mapped(itemgetter(idx))
    def attrgot(self, k):   return self.mapped(lambda o:getattr(o,k,0))
    def tensored(self):     return self.mapped(tensor)
    def stack(self, dim=0): return torch.stack(list(self.tensored()), dim=dim)
    def cat  (self, dim=0): return torch.cat  (list(self.tensored()), dim=dim)

defaults = SimpleNamespace()

def ifnone(a, b):
    "`b` if `a` is None else `a`"
    return b if a is None else a

def noop (x=None, *args, **kwargs):
    "Do nothing"
    return x

def noops(self, x, *args, **kwargs):
    "Do nothing (method)"
    return x

def tuplify(o, use_list=False, match=None):
    "Make `o` a tuple"
    return tuple(L(o, use_list=use_list, match=match))

def replicate(item,match):
    "Create tuple of `item` copied `len(match)` times"
    return (item,)*len(match)

def uniqueify(x, sort=False, bidir=False, start=None):
    "Return the unique elements in `x`, optionally `sort`-ed, optionally return the reverse correspondance."
    res = list(OrderedDict.fromkeys(x).keys())
    if start is not None: res = L(start)+res
    if sort: res.sort()
    if bidir: return res, {v:k for k,v in enumerate(res)}
    return res

def setify(o): return o if isinstance(o,set) else set(L(o))

def is_listy(x):
    "`isinstance(x, (tuple,list,L))`"
    return isinstance(x, (tuple,list,L,slice))

def range_of(x):
    "All indices of collection `x` (i.e. `list(range(len(x)))`)"
    return list(range(len(x)))

def mask2idxs(mask):
    "Convert bool mask or index list to index `L`"
    return L(_mask2idxs(mask))

def apply(func, x, *args, **kwargs):
    "Apply `func` recursively to `x`, passing on args"
    if is_listy(x): return [apply(func, o, *args, **kwargs) for o in x]
    if isinstance(x,dict):  return {k: apply(func, v, *args, **kwargs) for k,v in x.items()}
    return func(x, *args, **kwargs)

def to_detach(b, cpu=True):
    "Recursively detach lists of tensors in `b `; put them on the CPU if `cpu=True`."
    def _inner(x, cpu=True):
        if not isinstance(x,Tensor): return x
        x = x.detach()
        return x.cpu() if cpu else x
    return apply(_inner, b, cpu=cpu)

def to_half(b):
    "Recursively map lists of tensors in `b ` to FP16."
    return apply(lambda x: x.half() if x.dtype not in [torch.int64, torch.int32, torch.int16] else x, b)

def to_float(b):
    "Recursively map lists of int tensors in `b ` to float."
    return apply(lambda x: x.float() if x.dtype not in [torch.int64, torch.int32, torch.int16] else x, b)

defaults.device = torch.device('cuda',0) if torch.cuda.is_available else torch.device('cpu')

def to_device(b, device=defaults.device):
    "Recursively put `b` on `device`."
    def _inner(o): return o.to(device, non_blocking=True) if isinstance(o,Tensor) else o
    return apply(_inner, b)

def to_cpu(b):
    "Recursively map lists of tensors in `b ` to the cpu."
    return to_device(b,'cpu')

def item_find(x, idx=0):
    "Recursively takes the `idx`-th element of `x`"
    if is_listy(x): return item_find(x[idx])
    if isinstance(x,dict):
        key = list(x.keys())[idx] if isinstance(idx, int) else idx
        return item_find(x[key])
    return x

def find_device(b):
    "Recursively search the device of `b`."
    return item_find(b).device

def find_bs(b):
    "Recursively search the batch size of `b`."
    return item_find(b).shape[0]

@chk
def compose(*funcs: Callable, order=None):
    "Create a function that composes all functions in `funcs`, passing along remaining `*args` and `**kwargs` to all"
    funcs = L(funcs)
    if order is not None: funcs = funcs.sorted(order)
    def _inner(x, *args, **kwargs):
        for f in L(funcs): x = f(x, *args, **kwargs)
        return x
    return _inner

def mapper(f):
    "Create a function that maps `f` over an input collection"
    return lambda o: [f(o_) for o_ in o]

def partialler(f, *args, order=None, **kwargs):
    "Like `functools.partial` but also copies over docstring"
    fnew = partial(f,*args,**kwargs)
    fnew.__doc__ = f.__doc__
    if order is not None: fnew.order=order
    elif hasattr(f,'order'): fnew.order=f.order
    return fnew

def add_props(f, n=2):
    "Create properties passing each of `range(n)` to f"
    return (property(partial(f,i)) for i in range(n))

def make_cross_image(bw=True):
    "Create a tensor containing a cross image, either `bw` (True) or color"
    if bw:
        im = torch.zeros(5,5)
        im[2,:] = 1.
        im[:,2] = 1.
    else:
        im = torch.zeros(3,5,5)
        im[0,2,:] = 1.
        im[1,:,2] = 1.
    return im

#Comes from 02_data_pipeline.ipynb.
def opt_call(f, fname='__call__', *args, **kwargs):
    "Call `f.{fname}(*args, **kwargs)`, or `noop` if not defined"
    return getattr(f,fname,noop)(*args, **kwargs)

#Comes from 05_data_source.ipynb.
def all_union(sets):
    "Set of union of all `sets` (each `setified` if needed)"
    return set().union(*(map(setify,sets)))

#Comes from 05_data_source.ipynb.
def all_disjoint(sets):
    "`True` iif no element appears in more than one item of `sets`"
    return sum(map(len,sets))==len(all_union(sets))

#Comes from 12_learner.ipynb.
_camel_re1 = re.compile('(.)([A-Z][a-z]+)')
_camel_re2 = re.compile('([a-z0-9])([A-Z])')
def camel2snake(name):
    s1 = re.sub(_camel_re1, r'\1_\2', name)
    return re.sub(_camel_re2, r'\1_\2', s1).lower()

#Comes from 12_learner.ipynb.
def trainable_params(m):
    "Return all trainable parameters of `m`"
    return [p for p in m.parameters() if p.requires_grad]