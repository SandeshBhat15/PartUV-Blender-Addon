# must match PartUV demo: torch 2.7.1 cu128 (see https://github.com/EricWang12/PartUV)
TORCH_VERSION = "2.7.1"
# use CUDA 12.8 wheels as in PartUV README
TORCH_CUDA_INDEX = "https://download.pytorch.org/whl/cu128"
# without this page torch-scatter builds from source
TORCH_SCATTER_FIND_LINKS = f"https://data.pyg.org/whl/torch-{TORCH_VERSION}+cu128.html"
# independent of blender's python version
VENV_PYTHON = "3.11"


def _uv(uv, *args):
    """A uv command line. --no-config keeps a user's uv.toml, which can pin an
    index or an exclude-newer cutoff, out of the addon's venv."""
    return [uv, "--no-config", *args]


def build_install_commands(uv, venv_python, venv_path, wheel_url, ai, create_venv):
    """The uv command lines that put partuv and its deps in the managed venv."""
    commands = []
    if create_venv:
        commands.append(_uv(uv, "venv", "--python", VENV_PYTHON, venv_path))
    if ai:
        # uv keeps this over the extra's cpu pin - use cu128 for torch 2.7.1
        cuda_suffix = "cu128" if TORCH_VERSION == "2.7.1" else "cu121"
        commands.append(
            _uv(
                uv,
                "pip",
                "install",
                "--python",
                venv_python,
                "--index-url",
                TORCH_CUDA_INDEX,
                f"torch=={TORCH_VERSION}+{cuda_suffix}",
            )
        )
        requirement = f"partuv[ai] @ {wheel_url}"
        extra_args = ["-f", TORCH_SCATTER_FIND_LINKS]
    else:
        requirement = f"partuv @ {wheel_url}"
        extra_args = []
    commands.append(
        _uv(
            uv,
            "pip",
            "install",
            "--python",
            venv_python,
            "--upgrade",
            *extra_args,
            requirement,
        )
    )
    return commands
