// MongoDB initialization script for production
db = db.getSiblingDB('assignment_solver_prod');

// Create application user
db.createUser({
  user: 'app_user',
  pwd: process.env.MONGO_APP_PASSWORD || 'change_this_password',
  roles: [
    {
      role: 'readWrite',
      db: 'assignment_solver_prod'
    }
  ]
});

// Create collections with validation
db.createCollection('assignments', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['title', 'user_id', 'created_at', 'status'],
      properties: {
        title: {
          bsonType: 'string',
          description: 'Assignment title is required'
        },
        description: {
          bsonType: 'string'
        },
        subject: {
          bsonType: 'string'
        },
        user_id: {
          bsonType: 'string',
          description: 'User ID is required'
        },
        status: {
          bsonType: 'string',
          enum: ['pending', 'processing', 'completed', 'failed']
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation date is required'
        }
      }
    }
  }
});

db.createCollection('solutions', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['assignment_id', 'content', 'created_at'],
      properties: {
        assignment_id: {
          bsonType: 'string',
          description: 'Assignment ID is required'
        },
        content: {
          bsonType: 'string',
          description: 'Solution content is required'
        },
        explanation: {
          bsonType: 'string'
        },
        confidence_score: {
          bsonType: 'double',
          minimum: 0,
          maximum: 1
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation date is required'
        }
      }
    }
  }
});

db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['email', 'google_id', 'created_at'],
      properties: {
        email: {
          bsonType: 'string',
          pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
          description: 'Valid email is required'
        },
        google_id: {
          bsonType: 'string',
          description: 'Google ID is required'
        },
        name: {
          bsonType: 'string'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation date is required'
        }
      }
    }
  }
});

print('Database initialization completed successfully');