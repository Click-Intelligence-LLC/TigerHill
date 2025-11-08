"""
Code Generator

Generates test scripts from templates using Jinja2.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Template as Jinja2Template, Environment, StrictUndefined, TemplateError


class CodeGenerationError(Exception):
    """Raised when code generation fails"""
    pass


class CodeGenerator:
    """Generates code from templates"""

    def __init__(self, template):
        """
        Initialize generator with a template

        Args:
            template: Template object from TemplateLoader
        """
        self.template = template

        # Create Jinja2 environment
        self.env = Environment(
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Add custom filters
        self._add_custom_filters()

    def _add_custom_filters(self):
        """Add custom Jinja2 filters"""

        def snake_case(text: str) -> str:
            """Convert to snake_case"""
            import re
            # Replace hyphens with underscores
            text = text.replace('-', '_')
            # Insert underscore before capitals
            text = re.sub('([a-z])([A-Z])', r'\1_\2', text)
            return text.lower()

        def camel_case(text: str) -> str:
            """Convert to CamelCase"""
            parts = text.replace('-', '_').split('_')
            return ''.join(word.capitalize() for word in parts)

        def kebab_case(text: str) -> str:
            """Convert to kebab-case"""
            import re
            text = text.replace('_', '-')
            # Insert hyphen before capitals
            text = re.sub('([a-z])([A-Z])', r'\1-\2', text)
            return text.lower()

        self.env.filters['snake_case'] = snake_case
        self.env.filters['camel_case'] = camel_case
        self.env.filters['kebab_case'] = kebab_case

    def generate(
        self,
        params: Dict[str, Any],
        output_dir: str,
        overwrite: bool = False
    ) -> List[str]:
        """
        Generate files from template

        Args:
            params: Template parameters
            output_dir: Output directory for generated files
            overwrite: Whether to overwrite existing files

        Returns:
            List of generated file paths

        Raises:
            CodeGenerationError: If generation fails
        """
        output_path = Path(output_dir)

        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)

        generated_files = []

        # Process each file definition
        for file_def in self.template.files:
            file_path = file_def['path']
            template_name = file_def['template']

            # Render file path (may contain variables)
            try:
                rendered_path = self._render_string(file_path, params)
            except Exception as e:
                raise CodeGenerationError(
                    f"Failed to render file path '{file_path}': {e}"
                )

            # Get full output path
            full_path = output_path / rendered_path

            # Check if file exists
            if full_path.exists() and not overwrite:
                raise CodeGenerationError(
                    f"File already exists: {full_path} (use overwrite=True to replace)"
                )

            # Get template content
            template_content = self.template.get_template_content(template_name)
            if template_content is None:
                raise CodeGenerationError(
                    f"Template '{template_name}' not found in template file"
                )

            # Render template
            try:
                rendered_content = self._render_template(
                    template_content,
                    params
                )
            except Exception as e:
                raise CodeGenerationError(
                    f"Failed to render template '{template_name}': {e}"
                )

            # Write file
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_content)

                generated_files.append(str(full_path))

            except Exception as e:
                raise CodeGenerationError(
                    f"Failed to write file {full_path}: {e}"
                )

        return generated_files

    def _render_string(self, template_str: str, params: Dict[str, Any]) -> str:
        """
        Render a template string

        Args:
            template_str: Jinja2 template string
            params: Template parameters

        Returns:
            Rendered string
        """
        try:
            template = self.env.from_string(template_str)
            return template.render(**self._get_render_context(params))
        except TemplateError as e:
            raise CodeGenerationError(f"Template rendering error: {e}")

    def _render_template(
        self,
        template_content: str,
        params: Dict[str, Any]
    ) -> str:
        """
        Render a template with parameters

        Args:
            template_content: Jinja2 template content
            params: Template parameters

        Returns:
            Rendered content
        """
        try:
            template = self.env.from_string(template_content)
            return template.render(**self._get_render_context(params))
        except TemplateError as e:
            raise CodeGenerationError(f"Template rendering error: {e}")

    def _get_render_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get complete render context including parameters and metadata

        Args:
            params: User-provided parameters

        Returns:
            Complete context for template rendering
        """
        context = params.copy()

        # Add template metadata
        context['metadata'] = self.template.metadata
        context['dependencies'] = self.template.dependencies

        # Add each parameter's full definition for access in templates
        context['_parameters'] = {
            p['name']: p for p in self.template.parameters
        }

        return context

    def preview(self, params: Dict[str, Any]) -> Dict[str, str]:
        """
        Preview generated content without writing files

        Args:
            params: Template parameters

        Returns:
            Dictionary mapping file paths to rendered content
        """
        previews = {}

        for file_def in self.template.files:
            file_path = file_def['path']
            template_name = file_def['template']

            # Render file path
            try:
                rendered_path = self._render_string(file_path, params)
            except Exception as e:
                previews[file_path] = f"Error rendering path: {e}"
                continue

            # Get template content
            template_content = self.template.get_template_content(template_name)
            if template_content is None:
                previews[rendered_path] = f"Template '{template_name}' not found"
                continue

            # Render template
            try:
                rendered_content = self._render_template(
                    template_content,
                    params
                )
                previews[rendered_path] = rendered_content
            except Exception as e:
                previews[rendered_path] = f"Error rendering template: {e}"

        return previews

    def get_file_list(self, params: Dict[str, Any]) -> List[str]:
        """
        Get list of files that will be generated

        Args:
            params: Template parameters

        Returns:
            List of file paths (rendered)
        """
        files = []

        for file_def in self.template.files:
            file_path = file_def['path']
            try:
                rendered_path = self._render_string(file_path, params)
                files.append(rendered_path)
            except Exception:
                files.append(f"{file_path} (error rendering)")

        return files
