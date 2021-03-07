import json
import os
from importlib import import_module
from os.path import join
from typing import Any, Dict, List, Optional

import yaml
from jinja2 import Template
from mqtt_io.types import ConfigType

CONFIG_SCHEMA_PATH = "../mqtt_io/config/config.schema.yml"
DOCS_DIR = "docsify"
SIDEBAR_TEMPLATE = join(DOCS_DIR, "_sidebar.md.j2")
REF_TOC_ENTRIES: Dict[str, Dict[str, Any]] = {}


# TODO: Tasks pending completion -@flyte at 07/03/2021, 11:35:42
# Generate main repo readme and top level docs readme from the same template.
# Only add links to the documentation to the repo readme.
# Generate list of supported hardware from the modules themselves.


def title_id(entry_name: str, parents: List[str]) -> str:
    tid = ""
    if parents:
        tid += ("-".join(parents)) + "-"
    tid += entry_name
    return tid.replace("*", "star")


class ConfigSchemaParser:
    @staticmethod
    def parse_schema_section(
        section: ConfigType,
        container: List[Dict[str, Any]],
        parents: Optional[List[str]] = None,
    ) -> None:
        if parents is None:
            parents = []
        else:
            parents = parents.copy()

        child_schema = section.get("schema")
        if child_schema:
            parents.append("*")
            ConfigSchemaParser.parse_schema_section(child_schema, container, parents)
            return

        for entry_name in section.keys():
            entry: ConfigType = section[entry_name]
            ConfigSchemaParser.parse_cerberus_section(
                entry_name, entry, container, parents
            )

    @staticmethod
    def parse_cerberus_section(
        entry_name: str,
        section: ConfigType,
        container: List[Dict[str, Any]],
        parents: List[str],
    ) -> None:
        parents = parents.copy()
        child_schema = section.get("schema")

        children: List[Dict[str, Any]] = []
        toplevel_name = parents[0] if parents else entry_name

        depth = len([x for x in parents if x != "*"])
        container.append(
            dict(
                title=entry_name,
                children=children,
                depth=depth,
                path=f"config/reference/{toplevel_name}/",
            )
        )

        tid = title_id(entry_name, parents)
        section.setdefault("meta", {})["title_id"] = tid

        path = f"config/reference/{toplevel_name}/"
        if parents:
            path += f"?id={tid}"
            REF_TOC_ENTRIES[toplevel_name]["children"].append(
                dict(
                    title=entry_name,
                    element_id=tid,
                    orig_title=entry_name,
                    depth=depth,
                    path=path,
                    parents_str=".".join(parents),
                )
            )

        if child_schema:
            parents.append(entry_name)
            if "type" in child_schema:
                ConfigSchemaParser.parse_cerberus_section(
                    "*", child_schema, children, parents
                )
            else:
                ConfigSchemaParser.parse_schema_section(child_schema, children, parents)


def document_gpio_module() -> None:
    # TODO: Tasks pending completion -@flyte at 07/03/2021, 11:19:04
    # Continue writing this to document the modules in some way.
    module = import_module("mqtt_io.modules.gpio.raspberrypi")
    requirements = getattr(module, "REQUIREMENTS", None)
    config_schema = getattr(module, "CONFIG_SCHEMA", None)
    interrupt_support = getattr(module.GPIO, "INTERRUPT_SUPPORT", None)
    pin_schema = getattr(module.GPIO, "PIN_SCHEMA", None)
    input_schema = getattr(module.GPIO, "INPUT_SCHEMA", None)
    output_schema = getattr(module.GPIO, "OUTPUT_SCHEMA", None)


def main() -> None:
    print(f"Loading YAML config schema from '{CONFIG_SCHEMA_PATH}'...")
    with open(CONFIG_SCHEMA_PATH, "r") as config_schema_file:
        config_schema: ConfigType = yaml.safe_load(config_schema_file)

    print(f"Loading sidebar template from '{SIDEBAR_TEMPLATE}'...")
    with open(SIDEBAR_TEMPLATE, "r") as sidebar_template_file:
        sidebar_template: Template = Template(sidebar_template_file.read())

    top_level_section_names: List[str] = list(config_schema.keys())

    for section_name in top_level_section_names:
        REF_TOC_ENTRIES[section_name] = dict(
            title=section_name,
            orig_title=section_name,
            path=f"config/reference/{section_name}/",
            children=[],
        )

    ConfigSchemaParser.parse_schema_section(config_schema, [])

    ref_toc_list: List[Dict[str, Any]] = []

    for section_name in top_level_section_names:
        ref_toc_list.append(REF_TOC_ENTRIES[section_name])

    main_sidebar_path = join(DOCS_DIR, "_sidebar.md")
    print(f"Writing main sidebar file '{main_sidebar_path}'...")
    with open(main_sidebar_path, "w") as main_sidebar_file:
        main_sidebar_file.write(
            sidebar_template.render(dict(ref_sections=ref_toc_list, section=None))
        )

    for tl_section in top_level_section_names:
        section_path = join(DOCS_DIR, f"config/reference/{tl_section}")
        print(f"Making directory (if not exists) '{section_path}'...")
        os.makedirs(section_path, exist_ok=True)
        sidebar_path = join(section_path, "_sidebar.md")
        md_path = join(section_path, "README.md")
        print(f"Making section markdown file '{md_path}'...")
        with open(md_path, "w") as md_file:
            md_file.write(f'<schema-documentation section="{tl_section}" />\n')
        print(f"Making section sidebar file '{sidebar_path}'...")
        with open(sidebar_path, "w") as sb_file:
            sb_file.write(
                sidebar_template.render(
                    dict(ref_sections=ref_toc_list, section=tl_section)
                )
            )

    json_schema_path = join(DOCS_DIR, "schema.json")
    print(f"Making JSON config schema file '{json_schema_path}'...")
    with open(json_schema_path, "w") as json_schema_file:
        json.dump(config_schema, json_schema_file, indent=2)

    # generate_module_docs()


if __name__ == "__main__":
    main()
