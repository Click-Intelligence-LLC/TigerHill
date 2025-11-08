"""
Template Loader

Loads and parses YAML template files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


class TemplateLoadError(Exception):
    """Raised when template loading fails"""
    pass


class Template:
    """Represents a loaded template"""

    def __init__(self, data: Dict[str, Any], source_path: str):
        self.data = data
        self.source_path = source_path

        # Extract key sections
        self.metadata = data.get('metadata', {})
        self.parameters = data.get('parameters', [])
        self.dependencies = data.get('dependencies', {})
        self.files = data.get('files', [])
        self.templates = data.get('templates', {})

    @property
    def name(self) -> str:
        return self.metadata.get('name', 'unknown')

    @property
    def display_name(self) -> str:
        return self.metadata.get('display_name', self.name)

    @property
    def description(self) -> str:
        return self.metadata.get('description', '')

    @property
    def category(self) -> str:
        return self.metadata.get('category', 'general')

    @property
    def version(self) -> str:
        return self.metadata.get('version', '1.0.0')

    @property
    def tags(self) -> List[str]:
        return self.metadata.get('tags', [])

    def get_parameter(self, param_name: str) -> Optional[Dict]:
        """Get parameter definition by name"""
        for param in self.parameters:
            if param.get('name') == param_name:
                return param
        return None

    def get_template_content(self, template_name: str) -> Optional[str]:
        """Get template content by name"""
        return self.templates.get(template_name)

    def __repr__(self):
        return f"Template(name='{self.name}', category='{self.category}')"


class TemplateLoader:
    """Loads templates from the template directory"""

    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            # Default to templates/ directory in project root
            project_root = Path(__file__).parent.parent.parent
            templates_dir = project_root / "templates"

        self.templates_dir = Path(templates_dir)

        if not self.templates_dir.exists():
            raise TemplateLoadError(
                f"Templates directory not found: {self.templates_dir}"
            )

    def load_template(self, template_path: str) -> Template:
        """
        Load a single template from a path relative to templates_dir

        Args:
            template_path: Path to template file (e.g., "http/http-api-test.yaml")

        Returns:
            Template object

        Raises:
            TemplateLoadError: If template cannot be loaded
        """
        full_path = self.templates_dir / template_path

        if not full_path.exists():
            raise TemplateLoadError(f"Template file not found: {full_path}")

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise TemplateLoadError(
                    f"Invalid template format in {template_path}: expected dict"
                )

            # Validate required sections
            if 'metadata' not in data:
                raise TemplateLoadError(
                    f"Template {template_path} missing 'metadata' section"
                )

            if 'templates' not in data:
                raise TemplateLoadError(
                    f"Template {template_path} missing 'templates' section"
                )

            return Template(data, str(full_path))

        except yaml.YAMLError as e:
            raise TemplateLoadError(
                f"Failed to parse template {template_path}: {e}"
            )
        except Exception as e:
            raise TemplateLoadError(
                f"Failed to load template {template_path}: {e}"
            )

    def list_templates(self, category: Optional[str] = None) -> List[str]:
        """
        List all available templates

        Args:
            category: Optional category filter

        Returns:
            List of template paths (relative to templates_dir)
        """
        templates = []

        # Search for .yaml files
        if category:
            search_dir = self.templates_dir / category
            if not search_dir.exists():
                return []
            pattern = "*.yaml"
        else:
            search_dir = self.templates_dir
            pattern = "**/*.yaml"

        for yaml_file in search_dir.glob(pattern):
            # Skip catalog.yaml
            if yaml_file.name == 'catalog.yaml':
                continue

            # Get relative path
            rel_path = yaml_file.relative_to(self.templates_dir)
            templates.append(str(rel_path))

        return sorted(templates)

    def search_templates(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Template]:
        """
        Search templates by query, category, or tags

        Args:
            query: Search in name and description
            category: Filter by category
            tags: Filter by tags (any match)

        Returns:
            List of matching Template objects
        """
        all_paths = self.list_templates(category=category)
        results = []

        for path in all_paths:
            try:
                template = self.load_template(path)

                # Apply filters
                if query:
                    query_lower = query.lower()
                    if (query_lower not in template.name.lower() and
                        query_lower not in template.description.lower()):
                        continue

                if tags:
                    template_tags = set(template.tags)
                    search_tags = set(tags)
                    if not template_tags.intersection(search_tags):
                        continue

                results.append(template)

            except TemplateLoadError:
                # Skip invalid templates
                continue

        return results

    def get_categories(self) -> List[str]:
        """Get list of available template categories"""
        categories = []

        for item in self.templates_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                categories.append(item.name)

        return sorted(categories)
