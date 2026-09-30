"""Graphics settings (config.cfg) and ReShade install/preset, compared and synced between the two games."""
from __future__ import annotations

import configparser
import re
import shutil
from datetime import datetime
from pathlib import Path

from truckcfg import core, mods

USET_RE = re.compile(r'^uset (\w+) "(.*)"\s*$', re.M)

# (key, label, section) — the settings people actually tune; everything else graphics-related is still compared
CURATED = (
    ("r_mode_width", "Resolution width", "Display"), ("r_mode_height", "Resolution height", "Display"),
    ("r_fullscreen", "Fullscreen", "Display"), ("r_vsync", "In-game V-Sync", "Display"),
    ("t_limit_fps", "Frame limit", "Display"), ("r_scale_x", "Scaling", "Display"),
    ("r_aa", "Anti-aliasing mode", "Image"), ("r_anisotropy_factor", "Anisotropic filtering", "Image"),
    ("r_texture_detail", "Texture detail (0 = highest)", "Image"), ("r_normal_maps", "Normal maps", "Image"),
    ("r_dof", "Depth of field", "Image"), ("r_ssao", "Ambient occlusion", "Image"),
    ("r_sunshafts", "Sun shafts", "Image"), ("r_color_saturation", "Colour saturation", "Image"),
    ("g_bloom", "Bloom", "Image"),
    ("r_sun_shadow_texture_size", "Shadow resolution", "Shadows"), ("r_sun_shadow_quality", "Shadow quality", "Shadows"),
    ("r_fake_shadows", "Vehicle shadows", "Shadows"), ("r_interior_shadow", "Interior shadows", "Shadows"),
    ("g_reflection", "Reflection detail", "Reflections"), ("g_reflection_scale", "Reflection scaling", "Reflections"),
    ("g_rain_reflection", "Rain reflections", "Reflections"), ("r_mirror_view_distance", "Mirror draw distance", "Reflections"),
    ("r_mirror_group", "Mirror quality", "Reflections"),
    ("g_grass_density", "Grass density", "World"), ("g_veg_detail", "Vegetation detail", "World"),
    ("g_lod_factor_traffic", "Traffic detail", "World"), ("g_pedestrian", "Pedestrians", "World"),
)
LABELS = {k: (label, section) for k, label, section in CURATED}
_GFX_RE = re.compile(r"^(r_|g_(rain|reflection|grass|veg|bloom|lod|light|hq|menu_aa|truck_light|vehicle_flare|water)"
                     r"|t_limit_fps)")
_NOISE_RE = re.compile(r"^r_(multimon|manual_stereo|hmd|imgui|device|path|adapter|output|setup_done|startup|vulkan"
                       r"|deferred_debug|show_|tonemap_debug|hide_helpers|buffer_page|nowmi|minimal_unfinished"
                       r"|no_frame_tracking|ipd_scale)")


def config_path(game: core.Game) -> Path:
    return mods.game_dir(game) / "config.cfg"


def read_config(game: core.Game) -> dict[str, str]:
    p = config_path(game)
    return dict(USET_RE.findall(core.read_text(p))) if p.is_file() else {}


def is_graphics(key: str) -> bool:
    return key in LABELS or (bool(_GFX_RE.match(key)) and not _NOISE_RE.match(key))


def diff(src: dict[str, str], dst: dict[str, str]) -> list[dict]:
    """Graphics keys whose values differ. Curated ones first, in CURATED order."""
    keys = [k for k, *_ in CURATED] + sorted(k for k in set(src) | set(dst) if is_graphics(k) and k not in LABELS)
    out = []
    for k in keys:
        a, b = src.get(k), dst.get(k)
        if a is None and b is None:
            continue
        label, section = LABELS.get(k, (k, "Other"))
        out.append({"key": k, "label": label, "section": section, "curated": k in LABELS,
                    "a": a, "b": b, "same": a == b})
    return out


def write_keys(game: core.Game, values: dict[str, str]) -> Path:
    """Set uset values in config.cfg (adding missing ones). Backs the file up first; returns the backup path."""
    if core.is_running(game):
        raise RuntimeError(f"Close {game.title} first - it rewrites config.cfg when it exits.")
    p = config_path(game)
    text = core.read_text(p) if p.is_file() else "# prism3d variable config data\n\n"
    backup = p.with_name(f"config.cfg.bak-{datetime.now():%Y%m%d-%H%M%S}")
    if p.is_file():
        shutil.copy2(p, backup)
    pending = dict(values)

    def sub(m):
        k = m[1]
        return f'uset {k} "{pending.pop(k)}"' if k in pending else m[0]
    text = USET_RE.sub(sub, text)
    nl = "\r\n" if "\r\n" in text else "\n"
    text = text.rstrip("\r\n") + nl + "".join(f'uset {k} "{v}"{nl}' for k, v in pending.items())
    core.write_text_atomic(p, text)
    return backup


# ---------- ReShade ----------

RESHADE_FILES = ("dxgi.dll", "ReShade.ini", "ReShadePreset.ini")


def install_dir(game: core.Game) -> Path | None:
    for lib in mods.steam_libraries():
        d = lib / "steamapps" / "common" / game.title
        if d.is_dir():
            return d
    return None


def bin_dir(game: core.Game) -> Path | None:
    d = install_dir(game)
    return d / "bin" / "win_x64" if d else None


def reshade(game: core.Game) -> dict:
    b = bin_dir(game)
    if not b:
        return {"installed": False, "files": {}, "effects": [], "values": {}}
    files = {f: (b / f).is_file() for f in RESHADE_FILES}
    files["reshade-shaders"] = (b / "reshade-shaders").is_dir()
    effects, values = [], {}
    preset = b / "ReShadePreset.ini"
    if preset.is_file():
        cp = configparser.ConfigParser(strict=False, interpolation=None)
        cp.optionxform = str
        text = preset.read_text(encoding="utf-8", errors="replace")
        cp.read_string("[__top__]\n" + text)
        effects = [t.split("@")[0] for t in cp.get("__top__", "Techniques", fallback="").split(",") if t]
        for sec in cp.sections():
            if sec != "__top__":
                for k, v in cp.items(sec):
                    values[f"{sec} · {k}"] = v
    return {"installed": files["dxgi.dll"], "files": files, "effects": effects, "values": values}


def copy_reshade(src: core.Game, dst: core.Game) -> None:
    if core.is_running(dst):
        raise RuntimeError(f"Close {dst.title} first - it keeps ReShade's dxgi.dll loaded.")
    a, b = bin_dir(src), bin_dir(dst)
    if not (a and b and (a / "dxgi.dll").is_file()):
        raise RuntimeError(f"ReShade isn't installed in {src.title}.")
    for f in RESHADE_FILES:
        if (a / f).is_file():
            shutil.copy2(a / f, b / f)
    if (a / "reshade-shaders").is_dir():
        shutil.copytree(a / "reshade-shaders", b / "reshade-shaders", dirs_exist_ok=True)
