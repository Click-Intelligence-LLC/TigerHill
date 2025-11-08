"""
Template Catalog

Manages the template catalog and provides browsing/search functionality.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


class TemplateCatalog:
    """Manages template catalog"""

    def __init__(self, loader):
        """
        Initialize catalog with a TemplateLoader

        Args:
            loader: TemplateLoader instance
        """
        self.loader = loader
        self.catalog_path = Path(loader.templates_dir) / "catalog.yaml"
        self._catalog_data = None

    def load_catalog(self) -> Dict[str, Any]:
        """
        Load catalog file

        Returns:
            Catalog data dictionary
        """
        if self._catalog_data is not None:
            return self._catalog_data

        if not self.catalog_path.exists():
            # Generate catalog if it doesn't exist
            self._catalog_data = self.generate_catalog()
            return self._catalog_data

        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                self._catalog_data = yaml.safe_load(f)
            return self._catalog_data
        except Exception as e:
            raise Exception(f"Failed to load catalog: {e}")

    def generate_catalog(self) -> Dict[str, Any]:
        """
        Generate catalog from available templates

        Returns:
            Generated catalog data
        """
        catalog = {
            'version': '1.0.0',
            'categories': {},
            'templates': {}
        }

        # Get all categories
        categories = self.loader.get_categories()

        for category in categories:
            # Get templates in this category
            template_paths = self.loader.list_templates(category=category)

            if not template_paths:
                continue

            # Load first template to get category info (or use defaults)
            category_templates = []

            for path in template_paths:
                try:
                    template = self.loader.load_template(path)

                    # Add to templates index
                    template_id = template.name
                    catalog['templates'][template_id] = {
                        'path': path,
                        'name': template.display_name,
                        'description': template.description,
                        'category': category,
                        'tags': template.tags,
                        'version': template.version
                    }

                    category_templates.append(template_id)

                except Exception:
                    # Skip invalid templates
                    continue

            # Add category info
            if category_templates:
                catalog['categories'][category] = {
                    'name': category.replace('_', ' ').title(),
                    'description': f"Templates for {category} testing",
                    'templates': category_templates
                }

        return catalog

    def save_catalog(self):
        """Save current catalog to file"""
        if self._catalog_data is None:
            self._catalog_data = self.generate_catalog()

        try:
            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    self._catalog_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False
                )
        except Exception as e:
            raise Exception(f"Failed to save catalog: {e}")

    def get_categories(self) -> Dict[str, Dict]:
        """Get all categories with their metadata"""
        catalog = self.load_catalog()
        return catalog.get('categories', {})

    def get_category_templates(self, category: str) -> List[str]:
        """Get template IDs for a category"""
        catalog = self.load_catalog()
        categories = catalog.get('categories', {})

        if category not in categories:
            return []

        return categories[category].get('templates', [])

    def get_template_info(self, template_id: str) -> Optional[Dict]:
        """Get template metadata from catalog"""
        catalog = self.load_catalog()
        templates = catalog.get('templates', {})
        return templates.get(template_id)

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search templates in catalog

        Args:
            query: Search query for name/description
            category: Filter by category
            tags: Filter by tags

        Returns:
            List of matching template info dicts
        """
        catalog = self.load_catalog()
        templates = catalog.get('templates', {})
        results = []

        for template_id, template_info in templates.items():
            # Category filter
            if category and template_info.get('category') != category:
                continue

            # Query filter
            if query:
                query_lower = query.lower()
                name = template_info.get('name', '').lower()
                desc = template_info.get('description', '').lower()

                if query_lower not in name and query_lower not in desc:
                    continue

            # Tags filter
            if tags:
                template_tags = set(template_info.get('tags', []))
                search_tags = set(tags)
                if not template_tags.intersection(search_tags):
                    continue

            results.append({
                'id': template_id,
                **template_info
            })

        return results

    def list_all(self) -> List[Dict]:
        """List all templates"""
        return self.search()
