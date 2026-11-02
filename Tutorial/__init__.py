from . import lesson, keys, panel

modules = (lesson, keys, panel)


def register():
    for m in modules:
        m.register()


def unregister():
    for m in reversed(modules):
        m.unregister()
