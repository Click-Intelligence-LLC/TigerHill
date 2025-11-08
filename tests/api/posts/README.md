# REST CRUD Testing

Test complete CRUD operations (Create, Read, Update, Delete) on a REST API

## Generated Configuration

- **Agent Name**: `post-crud`
- **Base URL**: `http://localhost:3000`
- **Resource Path**: `/api/posts`
- **Resource Name**: `post`

## Operations Tested

1. **CREATE** - POST /api/posts
2. **READ** - GET /api/posts/{id}
3. **UPDATE** - PUT /api/posts/{id}
4. **DELETE** - DELETE /api/posts/{id}

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the test:

```bash
pytest test_post-crud.py -v
```

## Customization

Modify `create_data` and `update_data` to match your API's schema.

## Documentation

For more information, see:
- [TigerHill Documentation](https://github.com/yourusername/tigerhill)
- [HTTP Adapter Reference](https://github.com/yourusername/tigerhill/docs/adapters/http.md)