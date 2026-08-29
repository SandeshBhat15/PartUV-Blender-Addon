# Copyright (C) 2022-2026 Daniel Boxer
# See LICENSE for more information
#
# UVgami is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# UVgami is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with UVgami. If not, see <https://www.gnu.org/licenses/>.

import bpy
from .src.manager import manager
from .src.ops.start import UVGAMI_OT_start
from .src.ops.stop import (
    UVGAMI_OT_stop,
    UVGAMI_OT_cancel,
    UVGAMI_OT_cancel_all,
    UVGAMI_OT_cancel_background,
)
from .src.ops.guides import (
    UVGAMI_OT_draw_guides,
    UVGAMI_OT_seed_restrictions,
    UVGAMI_OT_exit_draw,
    UVGAMI_OT_clear_draw,
)
from .src.ops.uv import UVGAMI_OT_pack
from .src.ops.island import (
    UVGAMI_OT_unwrap_area,
    UVGAMI_OT_relax_area,
    UVGAMI_OT_combine_islands,
    UVGAMI_OT_unwrap_island,
    UVGAMI_OT_relax_island,
)
from .src.ops.misc import (
    UVGAMI_OT_expand,
    UVGAMI_OT_reset_setting,
    UVGAMI_OT_reset_settings,
    UVGAMI_OT_open_preferences,
    # start_symmetry_draw,
    # stop_symmetry_draw,
)
from .src.ops.grid import (
    UVGAMI_OT_add_grid,
    UVGAMI_OT_remove_grid,
)
from .src.ops.viewer import UVGAMI_OT_view_unwrap
from .src.ops.info import (
    UVGAMI_OT_clear_summary,
    UVGAMI_OT_open_logs,
)
from .src.ui.panels import (
    UVGAMI_PT_main,
    UVGAMI_PT_speed,
    UVGAMI_PT_weights,
    # UVGAMI_PT_symmetry,
    UVGAMI_PT_island_uv,
    UVGAMI_PT_island_settings,
    UVGAMI_PT_grid,
    UVGAMI_PT_pack,
    UVGAMI_PT_misc,
)
from .src.ui.props import (
    UVGAMI_PG_properties,
    UVGAMI_AP_preferences,
)
from .src.engines import ENGINES
from .src.engines.binary_engine import UVGAMI_OT_delete_engine
from .src.ui.oneclick import (
    PARTUV_OT_oneclick_install,
    PARTUV_OT_test_partuv,
    PARTUV_OT_verify_fix,
    PARTUV_PT_oneclick,
)


# every bpy class each engine needs registered (property groups and operators)
engine_classes = tuple(cls for engine in ENGINES.values() for cls in engine.classes)


classes = (
    PARTUV_OT_oneclick_install,
    PARTUV_OT_test_partuv,
    PARTUV_OT_verify_fix,
    PARTUV_PT_oneclick,
    UVGAMI_OT_start,
    UVGAMI_OT_stop,
    UVGAMI_OT_cancel_all,
    UVGAMI_OT_cancel_background,
    UVGAMI_OT_expand,
    UVGAMI_OT_open_preferences,
    UVGAMI_OT_add_grid,
    UVGAMI_OT_draw_guides,
    UVGAMI_OT_seed_restrictions,
    UVGAMI_OT_exit_draw,
    UVGAMI_OT_clear_draw,
    UVGAMI_OT_pack,
    UVGAMI_OT_unwrap_island,
    UVGAMI_OT_relax_island,
    UVGAMI_OT_combine_islands,
    UVGAMI_OT_unwrap_area,
    UVGAMI_OT_relax_area,
    UVGAMI_OT_cancel,
    UVGAMI_OT_remove_grid,
    UVGAMI_OT_view_unwrap,
    UVGAMI_OT_reset_setting,
    UVGAMI_OT_reset_settings,
    UVGAMI_OT_clear_summary,
    UVGAMI_OT_open_logs,
    UVGAMI_PT_main,
    UVGAMI_PT_weights,
    # UVGAMI_PT_symmetry,
    UVGAMI_PT_island_uv,
    UVGAMI_PT_island_settings,
    UVGAMI_PT_speed,
    UVGAMI_PT_grid,
    UVGAMI_PT_pack,
    UVGAMI_PT_misc,
    # shared by every binary engine, so it isn't in one engine's classes
    UVGAMI_OT_delete_engine,
    # engine groups must register before the main group that points to them
    *engine_classes,
    UVGAMI_PG_properties,
    UVGAMI_AP_preferences,
)


@bpy.app.handlers.persistent
def _on_load_pre(*args):
    # blender passes a different number of args by version, and none are needed.
    # load_pre, not post, so cleanup can still touch the objects it made
    manager.shutdown()


def _auto_install_if_needed():
    # Auto-install PartUV AI + xatlas on first enable - no extra user click.
    try:
        from .src.engines.partuv import get_installed_partuv_version, is_partuv_installed, is_partuv_ai_installed
        try: get_installed_partuv_version.cache_clear()
        except: pass
        if is_partuv_installed():
            # If already installed, check if AI is complete
            try:
                if is_partuv_ai_installed():
                    return  # fully ready
                # Check for incomplete AI install (checkpoint without torch)
                from .src.engines.partuv.paths import get_partuv_checkpoint_path, get_partuv_venv_path
                import pathlib, platform
                # Only auto-fix if checkpoint exists but torch is missing
                ckpt = get_partuv_checkpoint_path()
                venv = get_partuv_venv_path()
                site = venv / "Lib" / "site-packages" if platform.system() == "Windows" else venv / "lib" / "python3.11" / "site-packages"
                torch_missing = not (site / "torch").is_dir()
                if ckpt.is_file() and torch_missing:
                    print("[PartUV] Detected incomplete AI install (checkpoint without torch) - repairing...")
                else:
                    # Geometric-only install is valid, don't auto-reinstall
                    return
            except:
                return
        # Not installed or incomplete -> trigger One-Click with AI (main)
        import threading
        from .src.ui.oneclick import _install_all_sync, _state
        if _state.get("running"):
            return
        print("[PartUV] Auto-installing PartUV AI + xatlas (no user click needed)...")
        th = threading.Thread(target=_install_all_sync, args=(True,), daemon=True)
        th.start()
    except Exception as e:
        import traceback
        print("[PartUV] auto-install check failed:", e)
        traceback.print_exc()

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.uvgami = bpy.props.PointerProperty(type=UVGAMI_PG_properties)
    bpy.app.handlers.load_pre.append(_on_load_pre)
    # Cache extension path on main thread for background installs (thread-safe)
    try:
        from .src.utils.paths import get_extension_dir_path
        get_extension_dir_path()
    except: pass
    # Auto-install PartUV as main (no extra step for user)
    # Delay slightly so Blender finishes registering
    import threading
    threading.Timer(2.0, _auto_install_if_needed).start()
    # start_symmetry_draw()


def unregister():
    manager.shutdown()
    # stop_symmetry_draw()
    if _on_load_pre in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_on_load_pre)
    del bpy.types.Scene.uvgami
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
