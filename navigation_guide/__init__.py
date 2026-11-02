from . import operators, panel_nav, panel_tutorial, props

modules = (props, operators, panel_nav, panel_tutorial)


def register():
    for m in modules:
        m.register()


def unregister():
    for m in reversed(modules):
        m.unregister()
