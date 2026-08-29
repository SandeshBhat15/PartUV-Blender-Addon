import bpy, threading, traceback, pathlib

_state = {
    "running": False,
    "log": [],
    "last_error": "",
    "progress": "",
}

def _log(msg):
    _state["log"].append(msg)
    print("[OneClick-PartUV]", msg)
    if len(_state["log"]) > 80:
        _state["log"] = _state["log"][-80:]

def _install_all_sync(install_ai: bool):
    # Default to AI when called without explicit flag (addon is AI-main)
    if install_ai is None:
        install_ai = True
    _state["running"] = True
    _state["last_error"] = ""
    _state["progress"] = "Starting..."
    try:
        _state["progress"] = "Installing xatlas (300 KB)..."
        _log("Installing xatlas...")
        try:
            from ..engines.xatlas.install import XATLAS
            XATLAS.install()
            _log(f"xatlas {XATLAS.version} -> {XATLAS.install_dir()}")
        except Exception as e:
            _log(f"xatlas failed (non-fatal): {e}")
            traceback.print_exc()

        _state["progress"] = "Installing OptCuts (2 MB)..."
        _log("Installing OptCuts...")
        try:
            from ..engines.optcuts.install import OPTCUTS
            OPTCUTS.install()
            _log(f"OptCuts {OPTCUTS.version} installed")
        except Exception as e:
            _log(f"OptCuts failed (may be 404): {e}")

        # Install PartUV - ai=True installs torch+deps, ai=False is geometric only
        tier_label = "AI (~5GB, includes torch)" if install_ai else "Geometric (~200 MB)"
        _state["progress"] = f"Installing PartUV {tier_label}..."
        _log(f"Installing PartUV {tier_label}...")
        try:
            from ..engines.partuv.install import install_partuv, PARTUV_VERSION
            from ..engines.partuv import get_installed_partuv_version
            try: get_installed_partuv_version.cache_clear()
            except: pass
            install_partuv(ai=install_ai)
            try: get_installed_partuv_version.cache_clear()
            except: pass
            ver = get_installed_partuv_version()
            _log(f"PartUV {'AI' if install_ai else 'geometric'} {ver or PARTUV_VERSION} installed")
            try:
                from ..engines import invalidate_engine_caches
                invalidate_engine_caches()
            except: pass
        except Exception as e:
            _log(f"PartUV {'AI' if install_ai else 'geometric'} FAILED: {e}")
            traceback.print_exc()
            _state["last_error"] = str(e)
            raise

        # Checkpoint is already handled by install_partuv(ai=True), but keep
        # explicit download for resume cases and for geometric->AI upgrade
        if install_ai:
            _state["progress"] = "Verifying PartUV AI checkpoint (~1.2 GB)..."
            _log("Verifying AI checkpoint...")
            try:
                from ..engines.partuv.install import download_checkpoint
                download_checkpoint()
                _log("AI checkpoint ready")
            except Exception as e:
                _log(f"AI checkpoint failed: {e}")
                _state["last_error"] = str(e)
                # Don't fail whole install - torch is installed, checkpoint can be retried
                if "checkpoint" in str(e).lower():
                    _log("Torch installed OK; checkpoint can be re-downloaded from Addon Preferences")

        _state["progress"] = "Done OK PartUV is ready as main engine"
        _log("=== One-Click DONE - PartUV is now main engine ===")
    except Exception as e:
        _state["progress"] = f"Failed: {e}"
        _state["last_error"] = str(e)
        _log(f"FAILED: {e}")
    finally:
        _state["running"] = False


_verify_cache = {"t": 0.0, "v": (False, ["not checked"])}

def _verify_install():
    """Check all required files; return (fully_ready, issues list). Cached 1s to avoid heavy stat on every draw."""
    import time
    now = time.monotonic()
    if now - _verify_cache["t"] < 1.0 and not _state.get("running"):
        return _verify_cache["v"]
    issues = []
    try:
        from ..engines.partuv import get_installed_partuv_version, is_partuv_installed, is_partuv_ai_installed
        from ..engines.partuv.paths import get_partuv_venv_python, get_partuv_checkpoint_path
        from ..engines.xatlas.install import XATLAS
        from ..engines.optcuts.install import OPTCUTS
        try: get_installed_partuv_version.cache_clear()
        except: pass
        ver = get_installed_partuv_version()
        if not ver:
            issues.append("PartUV engine not installed")
        else:
            py = get_partuv_venv_python()
            if not py.is_file():
                issues.append("PartUV venv python missing")
            # torch + checkpoint check for AI (AI is main, so checkpoint required)
            ckpt = get_partuv_checkpoint_path()
            if ckpt.is_file():
                import pathlib, platform
                from ..engines.partuv.paths import get_partuv_venv_path
                venv = get_partuv_venv_path()
                site = venv / "Lib" / "site-packages" if platform.system() == "Windows" else venv / "lib" / "python3.11" / "site-packages"
                if not (site / "torch").is_dir():
                    issues.append("PartUV AI torch missing - needs repair")
                # checkpoint size sanity (1186 MB expected, <500MB is broken)
                try:
                    sz = ckpt.stat().st_size
                    if sz < 500_000_000:
                        issues.append(f"Checkpoint incomplete ({sz/1024/1024:.0f} MB)")
                except: pass
            else:
                # checkpoint missing - required for AI main
                # check if .part exists (downloading)
                part = ckpt.with_name(ckpt.name + ".part")
                if part.is_file():
                    try:
                        sz = part.stat().st_size
                        issues.append(f"AI checkpoint downloading ({sz/1024/1024:.0f} MB / 1186 MB)")
                    except:
                        issues.append("AI checkpoint downloading...")
                else:
                    issues.append("AI checkpoint not installed (1.2 GB)")
        # xatlas
        try:
            iv = XATLAS.installed_version()
            if not iv or not XATLAS.installed_path() or not XATLAS.installed_path().is_file():
                issues.append("xatlas not installed")
        except Exception as e:
            issues.append(f"xatlas check failed: {e}")
        # optcuts
        try:
            iv2 = OPTCUTS.installed_version()
            if not iv2 or not OPTCUTS.installed_path() or not OPTCUTS.installed_path().is_file():
                issues.append("OptCuts not installed")
        except Exception as e:
            issues.append(f"OptCuts check failed: {e}")
    except Exception as e:
        issues.append(f"verify failed: {e}")
    fully_ready = len(issues) == 0
    _verify_cache["t"] = now
    _verify_cache["v"] = (fully_ready, issues)
    return fully_ready, issues


def _is_fully_installed():
    ok, _ = _verify_install()
    return ok

class PARTUV_OT_oneclick_install(bpy.types.Operator):
    bl_idname = "partuv.oneclick_install"
    bl_label = "One-Click Install All (PartUV AI + xatlas + OptCuts)"
    bl_description = "Downloads PartUV AI (+5GB checkpoint) as MAIN, plus xatlas and OptCuts. PartUV uses AI segmentation by default"
    bl_options = {'REGISTER'}

    install_ai: bpy.props.BoolProperty(name="Include AI Checkpoint (~5GB)", default=True, description="Also download PartField AI checkpoint (non-commercial) for better islands - ON by default since addon is AI-main")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        layout = self.layout
        layout.label(text="PartUV AI will be MAIN engine:", icon='IMPORT')
        col = layout.column(align=True)
        col.label(text="- PartUV 0.1.4 AI (~200 MB + 1.2 GB checkpoint) * MAIN")
        col.label(text="- xatlas 0.2.3 (300 KB) fallback")
        col.label(text="- OptCuts 1.20.2 (2 MB)")
        if self.install_ai:
            col.label(text="- AI checkpoint model_objaverse.ckpt (~1.2 GB) - default ON")
        layout.prop(self, "install_ai")
        if _state["running"]:
            layout.label(text="Already running...", icon='TIME')

    def execute(self, context):
        if _state["running"]:
            self.report({'WARNING'}, "Already running")
            return {'CANCELLED'}
        t = threading.Thread(target=_install_all_sync, args=(self.install_ai,), daemon=True)
        t.start()
        self.report({'INFO'}, f"One-Click started ({'AI' if self.install_ai else 'Geometric'}) - see 3D View > N > PartUV for progress")
        return {'FINISHED'}

class PARTUV_OT_test_partuv(bpy.types.Operator):
    bl_idname = "partuv.test"
    bl_label = "Test PartUV (Original Demo)"
    bl_description = "Replicates: python demo/partuv_demo.py --mesh_path <selected> --segmentation ai --threshold 1.25 --pack_method blender - runs PartUV AI + blender pack as shown on https://github.com/EricWang12/PartUV"

    def execute(self, context):
        try:
            bpy.ops.object.select_all(action='DESELECT')
            if "Suzanne" not in bpy.data.objects:
                bpy.ops.mesh.primitive_monkey_add()
                suz = context.view_layer.objects.active
                suz.name = "Suzanne"
            suz = bpy.data.objects.get("Suzanne")
            bpy.ops.object.select_all(action='DESELECT')
            suz.select_set(True)
            context.view_layer.objects.active = suz
            bpy.ops.object.duplicate()
            dup = context.view_layer.objects.active
            dup.name = "Suzanne_PartUV"
            dup.location.x += 3
            bpy.ops.object.select_all(action='DESELECT')
            dup.select_set(True)
            context.view_layer.objects.active = dup
            # Ensure PartUV is selected as engine via props
            try:
                # Force engine to PARTUV via scene props (uses _engine_get/set, but we set stored)
                context.scene.uvgami["engine"] = 1  # PARTUV enum_value = 1
            except: pass
            # Use Bridge path if available, else try UVgami operator
            # The unified addon uses UVgami's partuv via venv; we can trigger via the manager by calling start operator
            # For quick test, use the partuv venv directly if Bridge not present
            # Try Bridge first (if external Bridge installed, else fallback to direct partuv CLI)
            try:
                # If separate Bridge exists, use it
                if "bl_ext.user_default.partuv_bridge" in bpy.context.preferences.addons:
                    res = bpy.ops.partuv.unwrap(mode='GEOMETRIC', threshold=1.25, use_fallback=False)
                    self.report({'INFO'}, f"Bridge unwrap {res}")
                else:
                    # Direct UVgami test: set engine to PartUV and check validate
                    from ..engines.partuv import get_installed_partuv_version, is_partuv_installed
                    try: get_installed_partuv_version.cache_clear()
                    except: pass
                    ver = get_installed_partuv_version()
                    if not is_partuv_installed():
                        self.report({'WARNING'}, "PartUV not installed yet, run One-Click Install first")
                        return {'CANCELLED'}
                    self.report({'INFO'}, f"PartUV v{ver} ready as main - use UVgami > Unwrap to test on {dup.name}")
                    return {'FINISHED'}
            except Exception as e:
                traceback.print_exc()
                self.report({'INFO'}, f"Test setup done, now unwrap {dup.name} via 3D View > N > PartUV > Unwrap (PartUV is main)")
                return {'FINISHED'}
            uvl = dup.data.uv_layers.active.data
            uu = [d.uv[0] for d in uvl]
            vv = [d.uv[1] for d in uvl]
            self.report({'INFO'}, f"PartUV OK {dup.name}: {len(dup.data.polygons)} polys, UV bbox U {min(uu):.2f}-{max(uu):.2f} V {min(vv):.2f}-{max(vv):.2f}")
            return {'FINISHED'}
        except Exception as e:
            traceback.print_exc()
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class PARTUV_OT_verify_fix(bpy.types.Operator):
    bl_idname = "partuv.verify_fix"
    bl_label = "Verify & Repair"
    bl_description = "Verify all engine files; reinstall any missing/corrupt files"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if _state["running"]:
            self.report({'WARNING'}, "Install already running")
            return {'CANCELLED'}
        fully, issues = _verify_install()
        if fully:
            self.report({'INFO'}, "All engines verified OK")
            return {'FINISHED'}
        # Fix: reinstall missing parts via One-Click AI (covers all)
        self.report({'INFO'}, f"Repairing: {', '.join(issues[:3])}")
        t = threading.Thread(target=_install_all_sync, args=(True,), daemon=True)
        t.start()
        return {'FINISHED'}

class PARTUV_PT_oneclick(bpy.types.Panel):
    bl_label = "PartUV - One-Click"
    bl_idname = "PARTUV_PT_oneclick"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PartUV"
    # Visible on main page by default so download progress is seen immediately
    bl_options = set()

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column(align=True)
        col.label(text="PartUV is MAIN engine", icon='UV')
        # Engine status (cached, no cache_clear on draw to avoid heavy stat)
        try:
            from ..engines.partuv import get_installed_partuv_version as gv
            ver = gv()
            col.label(text=f"PartUV: {ver} OK" if ver else "PartUV: not installed", icon='CHECKMARK' if ver else 'TIME')
            from ..engines import ENGINES
            for k in ["PARTUV","XATLAS","OPTCUTS"]:
                eng = ENGINES.get(k)
                if eng and hasattr(eng, "release"):
                    iv = eng.release.installed_version()
                    icon = 'CHECKMARK' if iv else 'DOT'
                    col.label(text=f"{k}: {iv or '-'}", icon=icon)
        except: pass

        if _state["running"]:
            box2 = layout.box()
            box2.label(text=_state["progress"], icon='TIME')
            # Show underlying download progress (bytes) from install_task - visible on main page
            try:
                from ..engines.install_task import task_state as ts
                phase = ts.get("phase") or _state["progress"]
                done = ts.get("bytes_done") or 0
                total = ts.get("bytes_total")
                if total:
                    pct = (done/total*100) if total else 0
                    box2.progress(factor=done/total, type='BAR', text=f"{phase} {done/1024/1024:.1f}/{total/1024/1024:.1f} MB {pct:.0f}%")
                elif done:
                    box2.label(text=f"{phase}: {done/1024/1024:.1f} MB")
                else:
                    box2.label(text=phase)
            except:
                pass
            for line in _state["log"][-4:]:
                box2.label(text=line[:58])
        elif _state["last_error"]:
            layout.label(text=_state["last_error"][:48], icon='ERROR')

        # Verify files; hide install button when everything is present
        try:
            fully_ready, issues = _verify_install()
        except:
            fully_ready, issues = False, []

        if fully_ready and not _state["running"]:
            # All required files verified - hide install button
            box = layout.box()
            box.label(text="All engines ready OK", icon='CHECKMARK')
            bcol = box.column(align=True)
            bcol.label(text="- PartUV AI + xatlas + OptCuts verified")
            bcol.label(text="- 3D View -> N -> PartUV -> Unwrap")
            bcol.label(text="- Uses PartUV as main, xatlas fallback")
            # Only show Test when ready; install is hidden
            layout.operator("partuv.test", text="Test PartUV", icon='PLAY')
            row = layout.row(align=True)
            row.scale_y = 0.9
            row.operator("partuv.verify_fix", text="Re-verify", icon='FILE_REFRESH')
        else:
            # Not fully installed - show issues and install options
            if issues and not _state["running"]:
                box = layout.box()
                box.label(text="Setup incomplete:", icon='ERROR')
                for iss in issues[:3]:
                    box.label(text=f"- {iss}", icon='DOT')
                box.operator("partuv.verify_fix", text="Verify & Repair", icon='TOOL_SETTINGS')

            col = layout.column(align=True)
            col.scale_y = 1.45
            op = col.operator("partuv.oneclick_install", text="One-Click Install AI (Recommended)", icon='IMPORT')
            op.install_ai = True
            row = layout.row(align=True)
            row.operator("partuv.oneclick_install", text="Geometric Only").install_ai = False
            row.operator("partuv.oneclick_install", text="+ AI (1.2 GB)").install_ai = True
            layout.operator("partuv.test", text="Test PartUV", icon='PLAY')
