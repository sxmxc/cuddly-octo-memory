import {
  buildDefaultParameterValue,
  buildRequestSchemaContract,
  createRequestParameterDefinition,
  extractRequestBodySchema,
  extractRequestParameterDefinitions,
  syncPathParameterDefinitions,
  validateRequestParameterDefinitions,
} from "./requestSchema";

describe("requestSchema utilities", () => {
  it("round-trips body, path, and query request sections through the shared contract", () => {
    const contract = buildRequestSchemaContract(
      {
        type: "object",
        properties: {
          name: {
            type: "string",
            minLength: 2,
          },
        },
        required: ["name"],
        "x-builder": { order: ["name"] },
      },
      {
        path: [
          createRequestParameterDefinition("path", {
            id: "path-item-id",
            name: "itemId",
            type: "integer",
            minimum: 1,
          }),
        ],
        query: [
          createRequestParameterDefinition("query", {
            id: "query-limit",
            name: "limit",
            type: "integer",
            required: true,
            minimum: 1,
          }),
          createRequestParameterDefinition("query", {
            id: "query-state",
            name: "state",
            type: "enum",
            enumValues: ["active", "archived"],
          }),
        ],
      },
    );

    expect(extractRequestBodySchema(contract)).toMatchObject({
      properties: {
        name: {
          type: "string",
          minLength: 2,
        },
      },
    });

    expect(extractRequestParameterDefinitions(contract, "path")).toMatchObject([
      {
        name: "itemId",
        type: "integer",
        required: true,
        minimum: 1,
      },
    ]);

    expect(extractRequestParameterDefinitions(contract, "query")).toMatchObject([
      {
        name: "limit",
        type: "integer",
        required: true,
        minimum: 1,
      },
      {
        name: "state",
        type: "enum",
        enumValues: ["active", "archived"],
      },
    ]);
  });

  it("syncs stored path parameter definitions back to the current route placeholders", () => {
    const synced = syncPathParameterDefinitions("/api/devices/{deviceId}/{serialNumber}", [
      createRequestParameterDefinition("path", {
        id: "path-device-id",
        name: "deviceId",
        type: "integer",
        minimum: 10,
      }),
      createRequestParameterDefinition("path", {
        id: "path-legacy",
        name: "legacyId",
        type: "string",
      }),
    ]);

    expect(synced).toMatchObject([
      {
        id: "path-device-id",
        name: "deviceId",
        type: "integer",
        minimum: 10,
        required: true,
      },
      {
        name: "serialNumber",
        type: "string",
        required: true,
      },
    ]);
  });

  it("validates duplicate and enum parameter definitions and builds preview defaults", () => {
    expect(
      validateRequestParameterDefinitions(
        [
          createRequestParameterDefinition("query", { name: "limit" }),
          createRequestParameterDefinition("query", { name: "limit" }),
        ],
        "query",
      ),
    ).toContain('Duplicate query parameter "limit"');

    expect(
      validateRequestParameterDefinitions(
        [
          createRequestParameterDefinition("query", {
            name: "state",
            type: "enum",
            enumValues: [],
          }),
        ],
        "query",
      ),
    ).toContain('Enum query parameter "state"');

    expect(
      buildDefaultParameterValue(
        createRequestParameterDefinition("path", {
          name: "deviceId",
          type: "integer",
        }),
      ),
    ).toBe("1");

    expect(
      buildDefaultParameterValue(
        createRequestParameterDefinition("path", {
          name: "deviceId",
          type: "string",
          format: "uuid",
        }),
      ),
    ).toBe("11111111-1111-4111-8111-111111111111");

    expect(
      buildDefaultParameterValue(
        createRequestParameterDefinition("path", {
          name: "messageId",
          type: "string",
          maxLength: 6,
        }),
      ),
    ).toBe("sample");
  });
});
