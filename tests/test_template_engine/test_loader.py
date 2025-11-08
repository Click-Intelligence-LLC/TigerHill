"""
Tests for TemplateLoader
"""

import pytest
from pathlib import Path
from tigerhill.template_engine.loader import TemplateLoader, TemplateLoadError, Template


class TestTemplateLoader:
    """Test TemplateLoader functionality"""

    @pytest.fixture
    def loader(self):
        """Create a template loader"""
        # Use project templates directory
        project_root = Path(__file__).parent.parent.parent
        templates_dir = project_root / "templates"
        return TemplateLoader(templates_dir=str(templates_dir))

    def test_load_template(self, loader):
        """Test loading a single template"""
        template = loader.load_template("http/http-api-test.yaml")

        assert isinstance(template, Template)
        assert template.name == "http-api-test"
        assert template.display_name == "HTTP API Testing"
        assert template.category == "http"
        assert len(template.parameters) > 0
        assert len(template.files) > 0

    def test_load_invalid_template(self, loader):
        """Test loading a non-existent template"""
        with pytest.raises(TemplateLoadError):
            loader.load_template("nonexistent/template.yaml")

    def test_list_templates(self, loader):
        """Test listing all templates"""
        templates = loader.list_templates()

        assert len(templates) >= 11  # We created 11 templates
        assert "http/http-api-test.yaml" in templates
        assert "cli/cli-basic.yaml" in templates
        assert "llm/llm-prompt-response.yaml" in templates

    def test_list_templates_by_category(self, loader):
        """Test listing templates by category"""
        http_templates = loader.list_templates(category="http")

        assert len(http_templates) >= 3  # http-api-test, http-rest-crud, http-auth-test
        assert all("http/" in t for t in http_templates)

    def test_search_templates_by_query(self, loader):
        """Test searching templates by query"""
        results = loader.search_templates(query="API")

        assert len(results) > 0
        assert any("api" in t.name.lower() or "api" in t.description.lower() for t in results)

    def test_search_templates_by_category(self, loader):
        """Test searching templates by category"""
        results = loader.search_templates(category="llm")

        assert len(results) >= 4  # 4 LLM templates
        assert all(t.category == "llm" for t in results)

    def test_search_templates_by_tags(self, loader):
        """Test searching templates by tags"""
        results = loader.search_templates(tags=["http", "api"])

        assert len(results) > 0
        assert all(any(tag in t.tags for tag in ["http", "api"]) for t in results)

    def test_get_categories(self, loader):
        """Test getting list of categories"""
        categories = loader.get_categories()

        assert "http" in categories
        assert "cli" in categories
        assert "llm" in categories
        assert "stdio" in categories
        assert "integration" in categories

    def test_template_properties(self, loader):
        """Test Template object properties"""
        template = loader.load_template("http/http-api-test.yaml")

        # Test metadata properties
        assert template.name == "http-api-test"
        assert template.display_name == "HTTP API Testing"
        assert template.version == "1.0.0"
        assert "http" in template.tags
        assert "api" in template.tags

        # Test parameters
        agent_param = template.get_parameter("agent_name")
        assert agent_param is not None
        assert agent_param["type"] == "string"
        assert agent_param["required"] is True

        # Test template content
        main_script = template.get_template_content("main_script")
        assert main_script is not None
        assert "pytest" in main_script
        assert "TraceStore" in main_script


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
