#AUTOGENERATED! DO NOT EDIT! File to edit: dev/50_data_block.ipynb (unless otherwise specified).

__all__ = ['DataBlock']

from ..imports import *
from ..test import *
from ..core import *
from .transform import *
from .pipeline import *
from .source import *
from .core import *
from .external import *
from ..notebook.showdoc import show_doc

from inspect import isfunction,ismethod

def _merge_tfms(*tfms):
    "Group the `tfms` in a single list, removing duplicates (from the same class) and instantiating"
    g = groupby(concat(*tfms), lambda o:
        o if isinstance(o, type) else o.__qualname__ if (isfunction(o) or ismethod(o)) else o.__class__)
    return L(v[-1] for k,v in g.items()).mapped(instantiate)

@docs
@funcs_kwargs
class DataBlock():
    "Generic container to quickly build `DataSource` and `DataBunch`"
    get_x=get_items=splitter=get_y = None
    _methods = 'get_items splitter get_y get_x'.split()
    def __init__(self, ts=None, **kwargs):
        types = L(getattr(self,'types',(float,float)) if ts is None else ts)
        self.default_type_tfms = types.mapped(
            lambda t: L(getattr(t,'create',None)) + L(getattr(t,'default_type_tfms',None)))
        self.default_ds_tfms = _merge_tfms(ToTensor, *types.attrgot('default_ds_tfms', L()))
        self.default_dl_tfms = _merge_tfms(Cuda    , *types.attrgot('default_dl_tfms', L()))

    def datasource(self, source, type_tfms=None):
        self.source = source
        items = (self.get_items or noop)(source)
        if isinstance(items,tuple):
            items = L(items).zipped()
            labellers = [itemgetter(i) for i in range_of(self.default_type_tfms)]
        else: labellers = [noop] * len(self.default_type_tfms)
        splits = (self.splitter or noop)(items)
        if self.get_x: labellers[0] = self.get_x
        if self.get_y: labellers[1] = self.get_y
        if type_tfms is None: type_tfms = [L() for t in self.default_type_tfms]
        type_tfms = L([self.default_type_tfms, type_tfms, labellers]).mapped_zip(
            lambda tt,tfm,l: L(l) + _merge_tfms(tt, tfm))
        return DataSource(items, tfms=type_tfms, filts=splits)

    def databunch(self, source, type_tfms=None, ds_tfms=None, dl_tfms=None, bs=16, **kwargs):
        dsrc = self.datasource(source, type_tfms=type_tfms)
        ds_tfms = _merge_tfms(self.default_ds_tfms, ds_tfms)
        dl_tfms = _merge_tfms(self.default_dl_tfms, dl_tfms)
        return dsrc.databunch(bs=bs, after_item=ds_tfms, after_batch=dl_tfms, **kwargs)

    _docs = dict(datasource="Create a `Datasource` from `source` with `tfms` and `tuple_tfms`",
                 databunch="Create a `DataBunch` from `source` with `tfms`")

MultiCategory.default_type_tfms = OneHotEncode