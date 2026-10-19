// MongoDB JSON Schema Validation definitions
// Fulfills Unit III & Unit VI requirement for database-level validation.

const transactionValidator = {
  $jsonSchema: {
    bsonType: "object",
    required: ["user_id", "category_id", "type", "amount", "transaction_date", "created_at"],
    properties: {
      user_id: {
        bsonType: "string",
        description: "Must be a string identifier matching the logged-in Django user"
      },
      category_id: {
        bsonType: "objectId",
        description: "Must be an ObjectId referencing categories._id"
      },
      type: {
        enum: ["income", "expense"],
        description: "Must be either 'income' or 'expense'"
      },
      amount: {
        bsonType: ["decimal", "double", "int", "long"],
        description: "Must be a positive numeric or Decimal128 value"
      },
      note: {
        bsonType: "string",
        maxLength: 500,
        description: "Optional note or description up to 500 characters"
      },
      transaction_date: {
        bsonType: "date",
        description: "ISODate representing when the transaction occurred"
      },
      receipt: {
        bsonType: "object",
        description: "Optional embedded receipt metadata demonstrating embedded documents",
        properties: {
          merchant: { bsonType: "string" },
          receipt_no: { bsonType: "string" },
          payment_method: { bsonType: "string" }
        }
      },
      tags: {
        bsonType: "array",
        description: "Optional array of string tags",
        items: {
          bsonType: "string"
        }
      },
      created_at: {
        bsonType: "date",
        description: "Timestamp when document was created"
      },
      updated_at: {
        bsonType: "date",
        description: "Timestamp when document was last modified"
      }
    }
  }
};

const categoryValidator = {
  $jsonSchema: {
    bsonType: "object",
    required: ["user_id", "name", "kind", "created_at"],
    properties: {
      user_id: {
        bsonType: "string",
        description: "Must be a string matching the owner Django user"
      },
      name: {
        bsonType: "string",
        minLength: 1,
        maxLength: 100,
        description: "Category display name (e.g., Food, Travel, Fees, Salary)"
      },
      kind: {
        enum: ["income", "expense", "both"],
        description: "Category type: income, expense, or both"
      },
      budget_monthly: {
        bsonType: ["decimal", "double", "int", "long"],
        description: "Optional monthly budget threshold"
      },
      created_at: {
        bsonType: "date",
        description: "Timestamp when category was created"
      }
    }
  }
};

// Export definitions for use in mongosh or Node.js
if (typeof module !== "undefined" && module.exports) {
  module.exports = { transactionValidator, categoryValidator };
}
