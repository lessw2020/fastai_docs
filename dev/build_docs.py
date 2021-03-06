#!/usr/bin/env python3
from local.notebook.export2html import convert_all
from local.script import *
import yaml, os, sys
from pathlib import Path

from sidebar_data import sidebar_d

def _leaf(k,v):
    url = 'external_url' if "http" in v else 'url'
    if url=='url': v=v+'.html'
    return {'title':k, url:v, 'output':'web,pdf'}

_k_names = ['folders', 'folderitems', 'subfolders', 'subfolderitems']
def _side_dict(title, data, level=0):
    k_name = _k_names[level]
    level += 1
    res = [(_side_dict(k, v, level) if isinstance(v,dict) else _leaf(k,v))
        for k,v in data.items()]
    return ({k_name:res} if not title
            else res if title.startswith('empty')
            else {'title': title, 'output':'web', k_name: res})

def _make_sidebar():
    "Making sidebar..."
    res = _side_dict('Sidebar', sidebar_d)
    res = {'entries': [res]}
    res_s = yaml.dump(res, default_flow_style=False)
    res_s = res_s.replace('- subfolders:', '  subfolders:').replace(' - - ', '   - ')
    res_s = """
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# Instead edit sidebar_d inside docs_src/tools/make_sidebar.ipynb,
# Then execute that notebook from the beginning to the end
# Finally commit the modified notebook and this autogenerated file
#
"""+res_s
    open('../docs/_data/sidebars/home_sidebar.yml', 'w').write(res_s)

@call_parse
def main(
    force_all:Param("Rebuild even notebooks that haven't changed", bool)=False
):
    convert_all(dest_path='../docs', force_all=force_all)
    _make_sidebar()

