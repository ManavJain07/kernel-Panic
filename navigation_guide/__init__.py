from . import goal_ops, operators, overlay, panel_nav, panel_tutorial, props, session

modules = (props, operators, goal_ops, session, overlay, panel_nav, panel_tutorial)


def register():
    for m in modules:
        m.register()


def unregister():
    for m in reversed(modules):
        m.unregister()
