If we submit the following as 1 tool and the openapi spec has multiple endpoints and operation ids, the result is the following:

Request

```bash
curl --location 'http://localhost:8000/tools/from-spec' \
--header 'Content-Type: application/json' \
--data '{
    "gateway_id": "samplegatewaysecond-s8qkj5fs2n",
    "tool_name": "testing-todos",
    "openapi_spec": {
    "openapi": "3.0.3",
    "info": {
        "title": "test-sample-todos",
        "description": "Sample API with todos, samples, and test-data endpoints",
        "version": "1.0.0"
    },
    "servers": [
        {
            "url": "https://dummyjson.com"
        }
    ],
    "paths": {
        "/samples": {
            "get": {
                "summary": "Get all samples",
                "operationId": "get-samples",
                "responses": {
                    "200": {
                        "description": "Successful response"
                    }
                }
            },
            "put": {
                "summary": "Update a sample",
                "operationId": "update-sample",
                "responses": {
                    "200": {
                        "description": "Sample updated successfully"
                    }
                }
            }
        },
        "/test-data": {
            "get": {
                "summary": "Get test data",
                "operationId": "get-test-data",
                "responses": {
                    "200": {
                        "description": "Successful response"
                    }
                }
            }
        }
    }
}
}'
```

Response

```json
{
    "status": "success",
    "tool_name": "testing-todos",
    "gateway_id": "samplegatewaysecond-s8qkj5fs2n",
    "openapi_spec_path": "openapi_specs/testing-todos_openapi.json",
    "message": "Tool 'testing-todos' successfully created and registered on gateway samplegatewaysecond-s8qkj5fs2n"
}
```

It will create a tool for each endpoint/operation id combination in the spec. In this case, 3 tools will be created:
![img_4.png](img_4.png)

*When you delete a target, it would delete all 3 tools associated with that target.*