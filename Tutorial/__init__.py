from . import access, lesson, panel

modules = (access, lesson, panel)


def register():
    for m in modules:
        m.register()


def unregister():
    for m in reversed(modules):
        m.unregister()
