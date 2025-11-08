"""
CLI Wizard for Template-based Test Generation

Interactive command-line tool for selecting templates and generating test scripts.
Supports both interactive and non-interactive modes, as well as batch generation from config files.
"""

import sys
import os
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

from .loader import TemplateLoader, Template
from .validator import TemplateValidator
from .generator import CodeGenerator
from .catalog import TemplateCatalog


class TemplateWizard:
    """Interactive wizard for template-based test generation"""

    def __init__(self, templates_dir: Optional[str] = None):
        self.loader = TemplateLoader(templates_dir=templates_dir)
        self.catalog = TemplateCatalog(self.loader)

    def run(self,
            template_name: Optional[str] = None,
            output_dir: str = "./tests",
            params: Optional[Dict[str, Any]] = None,
            non_interactive: bool = False,
            force: bool = False):
        """
        Run the wizard (interactive or non-interactive)

        Args:
            template_name: Optional template name to use directly
            output_dir: Output directory for generated files
            params: Pre-provided parameters (for non-interactive mode)
            non_interactive: If True, don't prompt for input
            force: If True, overwrite existing files
        """
        # Non-interactive mode
        if non_interactive or params is not None:
            return self._run_non_interactive(
                template_name=template_name,
                output_dir=output_dir,
                params=params or {},
                force=force
            )

        # Interactive mode
        print("=" * 60)
        print("🎯 TigerHill Test Generator")
        print("Create test scripts from templates")
        print("=" * 60)
        print()

        # Select template
        if template_name:
            template = self._load_template_by_name(template_name)
            if template is None:
                return
        else:
            template = self._select_template_interactive()
            if template is None:
                return

        # Show template info
        self._show_template_info(template)

        # Collect parameters
        params = self._collect_parameters(template)
        if params is None:
            return

        # Validate parameters
        validator = TemplateValidator(template)
        params = validator.apply_defaults(params)
        is_valid, errors = validator.validate(params)

        if not is_valid:
            print("\n❌ Validation errors:")
            for error in errors:
                print(f"  - {error}")
            return

        # Review configuration
        if not self._confirm_generation(template, params, output_dir):
            print("\n❌ Generation cancelled")
            return

        # Generate files
        try:
            generator = CodeGenerator(template)
            generated_files = generator.generate(
                params=params,
                output_dir=output_dir,
                overwrite=False
            )

            print("\n✅ Generated files:")
            for file_path in generated_files:
                print(f"   {file_path}")

            print("\n" + "=" * 60)
            print("Next steps:")
            print(f"1. cd {output_dir}")
            print("2. pip install -r requirements.txt")
            print("3. pytest -v")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Generation failed: {e}")

    def _load_template_by_name(self, template_name: str) -> Optional[Template]:
        """Load template by name"""
        try:
            # Try direct path first (add .yaml if not present)
            if "/" in template_name:
                template_path = template_name if template_name.endswith('.yaml') else f"{template_name}.yaml"
                return self.loader.load_template(template_path)

            # Search by name in catalog
            catalog_info = self.catalog.get_template_info(template_name)
            if catalog_info:
                return self.loader.load_template(catalog_info['path'])

            print(f"❌ Template not found: {template_name}")
            return None

        except Exception as e:
            print(f"❌ Failed to load template: {e}")
            return None

    def _select_template_interactive(self) -> Optional[Template]:
        """Interactively select a template"""
        # Get categories
        categories = self.catalog.get_categories()

        if not categories:
            print("❌ No templates available")
            return None

        # Select category
        print("Select template category:")
        cat_list = list(categories.items())
        for i, (cat_id, cat_info) in enumerate(cat_list, 1):
            print(f"  {i}. {cat_info['name']}: {cat_info['description']}")

        while True:
            try:
                choice = input("\nCategory (1-{}): ".format(len(cat_list))).strip()
                cat_idx = int(choice) - 1
                if 0 <= cat_idx < len(cat_list):
                    selected_category = cat_list[cat_idx][0]
                    break
                print("Invalid choice. Please try again.")
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Selection cancelled")
                return None

        # Get templates in category
        template_ids = self.catalog.get_category_templates(selected_category)

        if not template_ids:
            print(f"❌ No templates in category: {selected_category}")
            return None

        # Select template
        print(f"\nSelect template from {cat_list[cat_idx][1]['name']}:")
        templates_info = []
        for i, template_id in enumerate(template_ids, 1):
            info = self.catalog.get_template_info(template_id)
            templates_info.append(info)
            print(f"  {i}. {info['name']}: {info['description']}")

        while True:
            try:
                choice = input("\nTemplate (1-{}): ".format(len(templates_info))).strip()
                tmpl_idx = int(choice) - 1
                if 0 <= tmpl_idx < len(templates_info):
                    selected_template_info = templates_info[tmpl_idx]
                    break
                print("Invalid choice. Please try again.")
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Selection cancelled")
                return None

        # Load template
        try:
            template = self.loader.load_template(selected_template_info['path'])
            return template
        except Exception as e:
            print(f"❌ Failed to load template: {e}")
            return None

    def _show_template_info(self, template: Template):
        """Show template information"""
        print("\n" + "=" * 60)
        print(f"Template: {template.display_name}")
        print(f"{template.description}")
        print("=" * 60)

    def _collect_parameters(self, template: Template) -> Optional[Dict[str, Any]]:
        """Collect parameter values from user"""
        print("\n📋 Configure Parameters")
        print("-" * 60)

        params = {}

        try:
            for param_def in template.parameters:
                param_name = param_def['name']
                param_display = param_def.get('display_name', param_name)
                param_desc = param_def.get('description', '')
                param_type = param_def.get('type', 'string')
                param_required = param_def.get('required', False)
                param_default = param_def.get('default')

                # Build prompt
                prompt_parts = [f"\n{param_display}"]
                if param_desc:
                    prompt_parts.append(f"  ({param_desc})")

                if param_type == 'choice':
                    choices = param_def.get('choices', [])
                    prompt_parts.append(f"  Choices: {', '.join(str(c) for c in choices)}")

                if param_default is not None:
                    prompt_parts.append(f"  Default: {param_default}")

                if not param_required:
                    prompt_parts.append("  [Optional]")

                print("\n".join(prompt_parts))

                # Get input
                if param_type == 'boolean':
                    value = self._input_boolean(param_default)
                elif param_type == 'choice':
                    value = self._input_choice(param_def.get('choices', []), param_default)
                elif param_type == 'integer':
                    value = self._input_integer(param_default, param_def.get('validation', {}))
                elif param_type == 'float':
                    value = self._input_float(param_default, param_def.get('validation', {}))
                else:
                    value = self._input_string(param_default)

                # Handle optional parameters
                if value is None and not param_required:
                    continue

                if value is not None:
                    params[param_name] = value

            return params

        except KeyboardInterrupt:
            print("\n\n❌ Input cancelled")
            return None

    def _input_string(self, default: Optional[str] = None) -> Optional[str]:
        """Input a string value"""
        prompt = "> "
        value = input(prompt).strip()

        if not value and default is not None:
            return default

        return value if value else None

    def _input_boolean(self, default: Optional[bool] = None) -> Optional[bool]:
        """Input a boolean value"""
        default_str = "Y/n" if default is True else "y/N" if default is False else "y/n"
        prompt = f"({default_str}) > "

        while True:
            value = input(prompt).strip().lower()

            if not value and default is not None:
                return default

            if value in ['y', 'yes', 'true', '1']:
                return True
            elif value in ['n', 'no', 'false', '0']:
                return False
            else:
                print("Please enter y/n")

    def _input_choice(self, choices: List[Any], default: Optional[Any] = None) -> Optional[Any]:
        """Input a choice value"""
        while True:
            value = input("> ").strip()

            if not value and default is not None:
                return default

            if value in choices or value in [str(c) for c in choices]:
                return value

            print(f"Please choose from: {', '.join(str(c) for c in choices)}")

    def _input_integer(self, default: Optional[int] = None, validation: Dict = {}) -> Optional[int]:
        """Input an integer value"""
        while True:
            value_str = input("> ").strip()

            if not value_str and default is not None:
                return default

            try:
                value = int(value_str)

                # Validate range
                if 'min' in validation and value < validation['min']:
                    print(f"Value must be >= {validation['min']}")
                    continue

                if 'max' in validation and value > validation['max']:
                    print(f"Value must be <= {validation['max']}")
                    continue

                return value

            except ValueError:
                print("Please enter a valid integer")

    def _input_float(self, default: Optional[float] = None, validation: Dict = {}) -> Optional[float]:
        """Input a float value"""
        while True:
            value_str = input("> ").strip()

            if not value_str and default is not None:
                return default

            try:
                value = float(value_str)

                # Validate range
                if 'min' in validation and value < validation['min']:
                    print(f"Value must be >= {validation['min']}")
                    continue

                if 'max' in validation and value > validation['max']:
                    print(f"Value must be <= {validation['max']}")
                    continue

                return value

            except ValueError:
                print("Please enter a valid number")

    def _confirm_generation(self, template: Template, params: Dict[str, Any], output_dir: str) -> bool:
        """Confirm generation with review"""
        print("\n" + "=" * 60)
        print("📝 Review Configuration")
        print("=" * 60)

        for param_def in template.parameters:
            param_name = param_def['name']
            param_display = param_def.get('display_name', param_name)

            if param_name in params:
                value = params[param_name]
                print(f"{param_display:30s} {value}")

        print(f"\nOutput directory: {output_dir}")

        # Get list of files that will be generated
        generator = CodeGenerator(template)
        file_list = generator.get_file_list(params)

        print(f"\nFiles to generate:")
        for file_name in file_list:
            print(f"  - {file_name}")

        print()
        confirm = input("Generate test files? (Y/n) > ").strip().lower()

        return confirm in ['', 'y', 'yes']

    def _run_non_interactive(self,
                            template_name: str,
                            output_dir: str,
                            params: Dict[str, Any],
                            force: bool) -> bool:
        """
        Run generation in non-interactive mode

        Args:
            template_name: Template name or path
            output_dir: Output directory
            params: Parameters dict
            force: Overwrite existing files

        Returns:
            True if successful, False otherwise
        """
        # Load template
        if not template_name:
            print("❌ Error: --template is required in non-interactive mode")
            return False

        template = self._load_template_by_name(template_name)
        if template is None:
            return False

        # Load parameters from environment variables
        env_params = self._load_params_from_env(template)

        # Merge params (command line overrides environment)
        merged_params = {**env_params, **params}

        # Convert parameter types based on template definition
        merged_params = self._convert_param_types(template, merged_params)

        # Validate parameters
        validator = TemplateValidator(template)
        merged_params = validator.apply_defaults(merged_params)
        is_valid, errors = validator.validate(merged_params)

        if not is_valid:
            print(f"❌ Validation errors for template '{template.display_name}':")
            for error in errors:
                print(f"  - {error}")
            print("\nRequired parameters:")
            for param_def in template.parameters:
                if param_def.get('required', False):
                    param_name = param_def['name']
                    param_type = param_def.get('type', 'string')
                    param_desc = param_def.get('description', '')
                    print(f"  --param {param_name}=<{param_type}>  # {param_desc}")
            return False

        # Generate files
        try:
            generator = CodeGenerator(template)
            generated_files = generator.generate(
                params=merged_params,
                output_dir=output_dir,
                overwrite=force
            )

            print(f"✅ Generated {len(generated_files)} files from template '{template.display_name}':")
            for file_path in generated_files:
                print(f"   {file_path}")

            return True

        except Exception as e:
            print(f"❌ Generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_params_from_env(self, template: Template) -> Dict[str, Any]:
        """
        Load parameters from environment variables

        Environment variables should be named: TIGERHILL_<PARAM_NAME>
        Example: TIGERHILL_AGENT_NAME=my-agent

        Args:
            template: Template to load params for

        Returns:
            Dict of parameters from environment
        """
        params = {}
        prefix = "TIGERHILL_"

        for param_def in template.parameters:
            param_name = param_def['name']
            env_var = f"{prefix}{param_name.upper()}"

            if env_var in os.environ:
                value_str = os.environ[env_var]
                param_type = param_def.get('type', 'string')

                # Convert to appropriate type
                try:
                    if param_type == 'integer':
                        params[param_name] = int(value_str)
                    elif param_type == 'float':
                        params[param_name] = float(value_str)
                    elif param_type == 'boolean':
                        params[param_name] = value_str.lower() in ['true', '1', 'yes', 'y']
                    else:
                        params[param_name] = value_str
                except ValueError:
                    print(f"⚠️  Warning: Invalid value for {env_var}: {value_str}")

        return params

    def _convert_param_types(self, template: Template, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert parameter values to appropriate types based on template definition

        Args:
            template: Template with parameter definitions
            params: Parameters dict with string values

        Returns:
            Dict with converted values
        """
        converted = {}

        # Create a lookup for parameter definitions
        param_defs = {p['name']: p for p in template.parameters}

        for param_name, value in params.items():
            if param_name not in param_defs:
                # Keep unknown parameters as-is
                converted[param_name] = value
                continue

            param_def = param_defs[param_name]
            param_type = param_def.get('type', 'string')

            try:
                # Convert based on type
                if param_type == 'integer':
                    converted[param_name] = int(value)
                elif param_type == 'float':
                    converted[param_name] = float(value)
                elif param_type == 'boolean':
                    # Handle various boolean representations
                    if isinstance(value, bool):
                        converted[param_name] = value
                    else:
                        converted[param_name] = str(value).lower() in ['true', '1', 'yes', 'y']
                elif param_type == 'json':
                    # Try to parse as JSON
                    import json
                    if isinstance(value, str):
                        converted[param_name] = json.loads(value) if value.startswith('{') or value.startswith('[') else value
                    else:
                        converted[param_name] = value
                else:
                    # string, url, email, path, choice - keep as string
                    converted[param_name] = value

            except (ValueError, json.JSONDecodeError) as e:
                print(f"⚠️  Warning: Could not convert {param_name}={value} to {param_type}: {e}")
                converted[param_name] = value

        return converted

    def generate_from_config(self, config_path: str, force: bool = False) -> bool:
        """
        Generate tests from a YAML configuration file

        Args:
            config_path: Path to YAML configuration file
            force: Overwrite existing files

        Returns:
            True if all generations succeeded, False otherwise
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            if not config:
                print(f"❌ Empty configuration file: {config_path}")
                return False

            # Support both single template and batch templates
            if 'template' in config:
                # Single template mode
                return self._generate_single_from_config(config, force)
            elif 'templates' in config:
                # Batch mode
                return self._generate_batch_from_config(config, force)
            else:
                print("❌ Invalid configuration file. Must contain 'template' or 'templates' key.")
                return False

        except FileNotFoundError:
            print(f"❌ Configuration file not found: {config_path}")
            return False
        except yaml.YAMLError as e:
            print(f"❌ Invalid YAML file: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to generate from config: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_single_from_config(self, config: Dict[str, Any], force: bool) -> bool:
        """Generate from single template configuration"""
        template_name = config.get('template')
        output_dir = config.get('output', './tests')
        params = config.get('params', {})

        print(f"📝 Generating from template: {template_name}")

        return self._run_non_interactive(
            template_name=template_name,
            output_dir=output_dir,
            params=params,
            force=force
        )

    def _generate_batch_from_config(self, config: Dict[str, Any], force: bool) -> bool:
        """Generate from batch configuration"""
        templates_config = config.get('templates', [])
        output_base = config.get('output_base', './tests')
        shared_params = config.get('shared_params', {})

        if not templates_config:
            print("❌ No templates defined in configuration")
            return False

        print(f"📦 Batch generation: {len(templates_config)} templates")
        print("=" * 60)

        success_count = 0
        fail_count = 0

        for idx, template_config in enumerate(templates_config, 1):
            template_name = template_config.get('template')
            if not template_name:
                print(f"\n❌ Template {idx}: Missing 'template' key")
                fail_count += 1
                continue

            # Get template-specific params only
            params = template_config.get('params', {})

            # Resolve variables in params using shared_params
            params = self._resolve_variables(params, shared_params)

            # Output directory
            output_dir = template_config.get('output', '')
            if output_dir:
                # If relative, join with output_base
                if not os.path.isabs(output_dir):
                    output_dir = os.path.join(output_base, output_dir)
            else:
                output_dir = output_base

            print(f"\n[{idx}/{len(templates_config)}] {template_name} -> {output_dir}")

            success = self._run_non_interactive(
                template_name=template_name,
                output_dir=output_dir,
                params=params,
                force=force
            )

            if success:
                success_count += 1
            else:
                fail_count += 1

        print("\n" + "=" * 60)
        print(f"✅ Succeeded: {success_count}")
        print(f"❌ Failed: {fail_count}")
        print(f"📊 Total: {success_count + fail_count}")

        return fail_count == 0

    def _resolve_variables(self, params: Dict[str, Any], shared_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve variables in parameters

        Supports ${var_name} syntax to reference shared parameters
        Example: api_url: ${base_url}/users
        """
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and '${' in value:
                # Replace variables
                for var_name, var_value in shared_params.items():
                    placeholder = f"${{{var_name}}}"
                    if placeholder in value:
                        value = value.replace(placeholder, str(var_value))

            resolved[key] = value

        return resolved


def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(
        description="TigerHill Test Generator - Create test scripts from templates",
        epilog="""
Examples:
  # Interactive mode
  %(prog)s

  # List templates
  %(prog)s --list

  # Generate with parameters
  %(prog)s -t http/http-api-test -p agent_name=my-api -p api_url=http://localhost:3000

  # Use environment variables
  export TIGERHILL_AGENT_NAME=my-api
  export TIGERHILL_API_URL=http://localhost:3000
  %(prog)s -t http/http-api-test

  # Force overwrite
  %(prog)s -t http/http-api-test -p agent_name=my-api --force

  # Generate from config file
  %(prog)s --config tests/config.yaml

  # Batch generation
  %(prog)s --config tests/batch_config.yaml --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config', '-c',
        help="YAML configuration file for batch generation"
    )

    parser.add_argument(
        '--template', '-t',
        help="Template name or path (e.g., http/http-api-test)"
    )

    parser.add_argument(
        '--output', '-o',
        default="./tests",
        help="Output directory (default: ./tests)"
    )

    parser.add_argument(
        '--param', '-p',
        action='append',
        dest='params',
        metavar='KEY=VALUE',
        help="Set parameter value (format: key=value). Can be used multiple times."
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help="Overwrite existing files"
    )

    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help="Run in non-interactive mode (no prompts)"
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help="List available templates"
    )

    parser.add_argument(
        '--templates-dir',
        help="Custom templates directory"
    )

    args = parser.parse_args()

    # Create wizard
    wizard = TemplateWizard(templates_dir=args.templates_dir)

    # Generate from config file if requested
    if args.config:
        success = wizard.generate_from_config(args.config, force=args.force)
        sys.exit(0 if success else 1)

    # List templates if requested
    if args.list:
        catalog = wizard.catalog
        print("Available Templates:")
        print("=" * 60)

        for template_info in catalog.list_all():
            print(f"\n{template_info['id']}")
            print(f"  Name: {template_info['name']}")
            print(f"  Description: {template_info['description']}")
            print(f"  Category: {template_info['category']}")
            print(f"  Tags: {', '.join(template_info.get('tags', []))}")

        return

    # Parse parameters from --param arguments
    params = {}
    if args.params:
        for param_str in args.params:
            if '=' not in param_str:
                print(f"❌ Error: Invalid parameter format: {param_str}")
                print("   Expected format: key=value")
                sys.exit(1)

            key, value = param_str.split('=', 1)
            params[key.strip()] = value.strip()

    # Check if any TIGERHILL_* environment variables are set
    has_env_params = any(key.startswith('TIGERHILL_') for key in os.environ.keys())

    # Determine if non-interactive mode
    # Non-interactive if:
    # 1. --non-interactive flag is set
    # 2. Template is provided and parameters are provided via --param
    # 3. Template is provided and environment variables are set
    non_interactive = args.non_interactive or (args.template and (params or has_env_params))

    # Run wizard
    wizard.run(
        template_name=args.template,
        output_dir=args.output,
        params=params if params else None,
        non_interactive=non_interactive,
        force=args.force
    )


if __name__ == "__main__":
    main()
