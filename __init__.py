"""Material Workflow: host-safe contract imports, lazy Blender registration."""
bl_info = {"name": "Material Workflow", "author": "Blender AI", "version": (0, 9, 2), "blender": (5, 2, 0), "location": "View3D > Sidebar > Material Workflow", "category": "Material"}

def register():
    from . import ui, ui_batch, ui_handoff, procedural_ui, projection_ui
    ui.register()
    ui_batch.register()
    ui_handoff.register()
    procedural_ui.register()
    projection_ui.register()

def unregister():
    from . import ui, ui_batch, ui_handoff, procedural_ui, projection_ui
    projection_ui.unregister()
    procedural_ui.unregister()
    ui_handoff.unregister()
    ui_batch.unregister()
    ui.unregister()
