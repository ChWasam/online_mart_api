# Online Mart - Microservices E-Commerce Platform

A modern, event-driven microservices architecture for an e-commerce platform built with FastAPI, Apache Kafka, and PostgreSQL.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technologies](#technologies)
- [Services](#services)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Service Communication](#service-communication)
- [Authentication](#authentication)
- [Database Schema](#database-schema)
- [Development](#development)
- [Contributing](#contributing)

## Overview

Online Mart is a distributed e-commerce platform that demonstrates microservices architecture best practices. The system is composed of six independent services that communicate asynchronously through Apache Kafka, each with its own database following the database-per-service pattern.

### Key Features

- **Product Management**: Full CRUD operations for product catalog
- **Inventory Tracking**: Real-time stock level management and reservations
- **Order Processing**: Complete order lifecycle management with status tracking
- **User Authentication**: JWT-based authentication with secure password hashing
- **Payment Processing**: Integrated payment handling with status tracking
- **Email Notifications**: Automated notifications for key business events
- **Event-Driven Architecture**: Asynchronous communication via Kafka
- **Scalable Design**: Horizontally scalable microservices

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Product    │  │  Inventory   │  │   Order      │  │
│  │   Service    │  │   Service    │  │   Service    │  │
│  │  Port: 8000  │  │  Port: 8001  │  │  Port: 8002  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    User      │  │   Payment    │  │ Notification │  │
│  │   Service    │  │   Service    │  │   Service    │  │
│  │  Port: 8003  │  │  Port: 8005  │  │  Port: 8004  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
│         └──────────────────┼──────────────────┘          │
│                            │                            │
│                    ┌───────▼────────┐                   │
│                    │  Kafka Broker  │                   │
│                    │  Port: 9092    │                   │
│                    │   + Kafka UI   │                   │
│                    │  Port: 8080    │                   │
│                    └────────────────┘                   │
│                                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │PostgreSQL│ │PostgreSQL│ │PostgreSQL│ │PostgreSQL│   │
│  │ Product  │ │Inventory │ │  Order   │ │   User   │   │
│  │   5433   │ │   5434   │ │   5435   │ │   5436   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                           │
│  ┌──────────┐                                            │
│  │PostgreSQL│                                            │
│  │ Payment  │                                            │
│  │   5437   │                                            │
│  └──────────┘                                            │
└─────────────────────────────────────────────────────────┘
```

### Architecture Principles

- **Microservices Pattern**: Independent, loosely coupled services
- **Database per Service**: Each service maintains its own database
- **Event-Driven Communication**: Asynchronous messaging via Kafka
- **API Gateway Ready**: Each service exposes RESTful APIs
- **Containerization**: Docker-based deployment for consistency

## Technologies

### Backend Framework
- **FastAPI** (0.111.0) - Modern Python web framework
- **Uvicorn** (0.30.0) - ASGI server
- **SQLModel** (0.0.18) - SQL ORM with Pydantic validation

### Data Layer
- **PostgreSQL** (latest) - Relational database (one per service)
- **Psycopg** (3.1.19) - PostgreSQL adapter

### Message Queue
- **Apache Kafka** (3.7.0) - Event streaming platform
- **aiokafka** (0.10.0) - Async Kafka client

### Serialization
- **Protocol Buffers** (5.27.0) - Efficient message serialization

### Authentication & Security
- **python-jose** (3.3.0) - JWT token handling
- **passlib** (1.7.4) - Password hashing with bcrypt

### DevOps
- **Docker** & **Docker Compose** - Containerization
- **Poetry** - Dependency management

## Services

### 1. Product Service (Port 8000)

Manages the product catalog and product information.

**Responsibilities:**
- Product CRUD operations
- Product availability tracking
- Product catalog management

**Key Endpoints:**
- `GET /products` - List all products
- `GET /product/{product_id}` - Get product details
- `POST /product` - Create new product
- `PUT /product/{product_id}` - Update product
- `DELETE /product/{product_id}` - Delete product

**Database:** `wasam_database_product` (Port 5433)

### 2. Inventory Service (Port 8001)

Tracks stock levels and manages inventory.

**Responsibilities:**
- Stock level management
- Inventory reservations
- Stock availability validation
- Product-inventory synchronization

**Key Endpoints:**
- `GET /inventory` - List all inventory
- `GET /inventory/{inventory_id}` - Get inventory details
- `POST /inventory/{product_id}` - Create inventory record
- `PUT /inventory/{inventory_id}` - Update stock levels

**Database:** `wasam_database_inventory` (Port 5434)

### 3. Order Service (Port 8002)

Orchestrates order creation and management.

**Responsibilities:**
- Order lifecycle management
- Order status tracking
- Payment status monitoring
- User validation
- Service orchestration

**Key Endpoints:**
- `GET /orders` - Get user's orders (Auth required)
- `GET /order/{order_id}` - Get order details (Auth required)
- `POST /order/{product_id}` - Create order (Auth required)
- `PUT /order/{order_id}` - Update order (Auth required)
- `DELETE /order/{order_id}` - Delete order (Auth required)
- `POST /user/login` - User login
- `GET /user/me` - Get current user (Auth required)
- `POST /user/refresh_token` - Refresh JWT token

**Database:** `wasam_database_order` (Port 5435)

### 4. User Service (Port 8003)

Handles user authentication and profile management.

**Responsibilities:**
- User registration
- Authentication and authorization
- JWT token generation
- Password hashing and verification
- User profile management

**Key Endpoints:**
- `POST /user/register` - Register new user
- `POST /user/login` - User login
- `GET /user/me` - Get current user (Auth required)

**Database:** `wasam_database_user` (Port 5436)

### 5. Payment Service (Port 8005)

Processes payments and manages payment status.

**Responsibilities:**
- Payment processing
- Payment status tracking
- User validation for payments
- Order payment confirmation

**Key Endpoints:**
- `PUT /payment` - Process payment (Auth required)

**Features:**
- Simulated payment gateway (90% success rate)
- Payment status tracking (PENDING, PAID, FAILED)

**Database:** `wasam_database_payment` (Port 5437)

### 6. Notification Service (Port 8004)

Sends email notifications for business events.

**Responsibilities:**
- Registration confirmation emails
- Order confirmation emails
- Payment confirmation emails
- Event-driven email delivery

**Email Events:**
- User registration
- Order creation
- Payment completion

**Configuration:**
- SMTP: Gmail (smtp.gmail.com:465)
- Requires app password configuration

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- Poetry (for dependency management)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd online_mart
   ```

2. **Configure environment variables**

   Each service directory contains a `.env` file. Update the following configurations:

   - Database credentials (default: `wasam`/`wasam_password`)
   - JWT secret key
   - SMTP credentials for notification service
   - Kafka bootstrap servers

3. **Start all services**
   ```bash
   docker-compose up --build
   ```

4. **Verify services are running**
   ```bash
   # Check service health
   curl http://localhost:8000  # Product Service
   curl http://localhost:8001  # Inventory Service
   curl http://localhost:8002  # Order Service
   curl http://localhost:8003  # User Service
   curl http://localhost:8004  # Notification Service
   curl http://localhost:8005  # Payment Service
   ```

5. **Access Kafka UI**

   Open http://localhost:8080 to monitor Kafka topics and messages

### Service Ports

| Service | Port | Public Access |
|---------|------|---------------|
| Product Service | 8000 | Yes |
| Inventory Service | 8001 | Yes |
| Order Service | 8002 | Yes |
| User Service | 8003 | Yes |
| Notification Service | 8004 | Yes |
| Payment Service | 8005 | Yes |
| Kafka (External) | 9092 | Yes |
| Kafka UI | 8080 | Yes |
| PostgreSQL (Product) | 5433 | Yes |
| PostgreSQL (Inventory) | 5434 | Yes |
| PostgreSQL (Order) | 5435 | Yes |
| PostgreSQL (User) | 5436 | Yes |
| PostgreSQL (Payment) | 5437 | Yes |

## API Documentation

### Interactive API Documentation

Each service provides interactive API documentation via Swagger UI:

- Product Service: http://localhost:8000/docs
- Inventory Service: http://localhost:8001/docs
- Order Service: http://localhost:8002/docs
- User Service: http://localhost:8003/docs
- Notification Service: http://localhost:8004/docs
- Payment Service: http://localhost:8005/docs

### Example Workflows

#### 1. User Registration and Login

```bash
# Register a new user
curl -X POST "http://localhost:8003/user/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }'

# Login to get JWT token
curl -X POST "http://localhost:8002/user/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=securepassword123"
```

#### 2. Create Product and Inventory

```bash
# Create a product
curl -X POST "http://localhost:8000/product" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop",
    "description": "High-performance laptop",
    "price": 999.99
  }'

# Create inventory for the product (use product_id from response)
curl -X POST "http://localhost:8001/inventory/{product_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_level": 100
  }'
```

#### 3. Create Order (Authenticated)

```bash
# Create an order (requires JWT token)
curl -X POST "http://localhost:8002/order/{product_id}" \
  -H "Authorization: Bearer {your_jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 2,
    "shipping_address": "123 Main St, City, Country",
    "customer_notes": "Please deliver in the morning"
  }'
```

#### 4. Process Payment (Authenticated)

```bash
# Process payment for an order
curl -X PUT "http://localhost:8005/payment" \
  -H "Authorization: Bearer {your_jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "{order_uuid}",
    "card_number": "4242424242424242",
    "card_expiry": "12/25",
    "card_cvv": "123"
  }'
```

## Service Communication

### Kafka Topics

Services communicate asynchronously through Kafka topics:

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `product` | Product API | Product Consumer | Product operations |
| `inventory` | Inventory API | Inventory Consumer | Inventory operations |
| `order` | Order API | Order Consumer | Order operations |
| `inventory_check_request` | Order Service | Inventory Consumer | Stock validation |
| `inventory_check_response` | Inventory Consumer | Order Consumer | Stock validation results |
| `user` | Order/Payment Services | User Consumer | User data requests |
| `response_from_user_to_order` | User Consumer | Order Consumer | User data for orders |
| `response_from_user_to_payment` | User Consumer | Payment Consumer | User data for payments |
| `payment` | Payment API | Payment Consumer | Payment operations |
| `payment_get` | Payment Consumer | Order/Payment API | Payment responses |
| `user_registration` | User Consumer | Notification Consumer | Registration events |
| `order_created` | Order Consumer | Notification Consumer | Order creation events |
| `payment_done` | Payment Consumer | Notification Consumer | Payment completion events |

### Message Serialization

All inter-service messages use **Protocol Buffers (proto3)** for efficient serialization:

- Binary format for reduced message size
- Strong typing and validation
- Schema versioning support
- Language-agnostic compatibility

### Communication Flows

#### Order Creation Flow
```
Client → Order Service (POST /order)
  → User Service (validate user via Kafka)
  → Order DB (create order)
  → Notification Service (send order confirmation email)
```

#### Payment Processing Flow
```
Client → Payment Service (PUT /payment)
  → User Service (validate user via Kafka)
  → Payment Gateway (process payment)
  → Order Service (update payment status via Kafka)
  → Notification Service (send payment confirmation email)
```

## Authentication

### JWT-Based Authentication

The system uses JSON Web Tokens (JWT) for authentication:

**Token Configuration:**
- Algorithm: HS256
- Expiry: 15 minutes (configurable)
- Refresh token support available

**Protected Endpoints:**
- All Order Service endpoints (except login)
- Payment Service endpoints
- User profile endpoints

**Token Usage:**
```bash
Authorization: Bearer {access_token}
```

### Password Security

- Passwords hashed using **bcrypt** algorithm
- Salt automatically generated per password
- Secure password verification via passlib

### Token Refresh

```bash
# Refresh expired token
curl -X POST "http://localhost:8002/user/refresh_token" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "{your_refresh_token}"
  }'
```

## Database Schema

### Product Service

```sql
Table: Product
- id: INTEGER (Primary Key)
- product_id: UUID (Indexed, Unique)
- name: VARCHAR (Indexed)
- description: TEXT (Indexed)
- price: FLOAT (Indexed)
- is_available: BOOLEAN
```

### Inventory Service

```sql
Table: Inventory
- id: INTEGER (Primary Key)
- inventory_id: UUID (Indexed, Unique)
- product_id: UUID (Indexed, Foreign Reference)
- stock_level: INTEGER (Indexed)
- reserved_stock: INTEGER (Indexed)
```

### Order Service

```sql
Table: Orders
- id: INTEGER (Primary Key)
- order_id: UUID (Indexed, Unique)
- product_id: UUID (Indexed)
- user_id: UUID (Indexed)
- quantity: INTEGER (Indexed)
- shipping_address: VARCHAR (Indexed)
- customer_notes: TEXT (Indexed)
- order_status: ENUM (IN_PROGRESS, COMPLETED)
- payment_status: ENUM (PENDING, PAID, FAILED)
```

### User Service

```sql
Table: User
- id: INTEGER (Primary Key)
- user_id: UUID (Indexed, Unique)
- username: VARCHAR (Indexed, Unique)
- email: VARCHAR (Indexed, Unique)
- password: VARCHAR (Hashed)
```

### Payment Service

```sql
Table: Payment
- id: INTEGER (Primary Key)
- payment_id: UUID (Indexed, Unique)
- order_id: UUID (Indexed)
- user_id: UUID (Indexed)
- payment_status: VARCHAR (Pending, Paid, Failed)
```

### Database Credentials

**Default Configuration:**
- Username: `wasam`
- Password: `wasam_password`
- Connection pooling: 10 connections per service
- Pool recycle: 300 seconds

## Development

### Local Development Setup

1. **Install Python dependencies**
   ```bash
   cd {service_name}_service
   poetry install
   ```

2. **Run service locally**
   ```bash
   poetry run uvicorn app.main:app --reload --port {service_port}
   ```

3. **Hot Reload**

   The Docker development setup includes volume mounts for hot reloading:
   - Code changes automatically trigger service restart
   - No need to rebuild containers during development

### Project Structure

```
online_mart/
├── product_service/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── api.py               # API endpoints
│   │   ├── consumers.py         # Kafka consumers
│   │   ├── producer.py          # Kafka producer
│   │   ├── models.py            # Database models
│   │   └── proto/               # Protocol Buffer definitions
│   ├── Dockerfile.dev
│   ├── pyproject.toml
│   └── .env
├── inventory_service/
│   └── (similar structure)
├── order_service/
│   └── (similar structure)
├── user_service/
│   └── (similar structure)
├── payment_service/
│   └── (similar structure)
├── notification_service/
│   └── (similar structure)
└── compose.yml
```

### Testing

(Testing framework to be implemented)

Recommended testing stack:
- **pytest** for unit tests
- **pytest-asyncio** for async tests
- **httpx** for API testing
- **testcontainers** for integration tests

### Code Quality

Recommended tools:
- **black** - Code formatting
- **pylint** - Code linting
- **mypy** - Type checking
- **isort** - Import sorting

## Monitoring and Debugging

### Kafka UI Dashboard

Access the Kafka UI at http://localhost:8080 to:
- Monitor topic messages
- View consumer groups
- Inspect message contents
- Debug message flow

### Database Access

Connect to PostgreSQL instances directly:
```bash
# Product Database
psql -h localhost -p 5433 -U wasam -d wasam_database_product

# Inventory Database
psql -h localhost -p 5434 -U wasam -d wasam_database_inventory

# Order Database
psql -h localhost -p 5435 -U wasam -d wasam_database_order

# User Database
psql -h localhost -p 5436 -U wasam -d wasam_database_user

# Payment Database
psql -h localhost -p 5437 -U wasam -d wasam_database_payment
```

### Logs

View service logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f product_service
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using the port
   lsof -i :{port_number}

   # Kill the process or change port in compose.yml
   ```

2. **Database connection errors**
   - Verify PostgreSQL containers are running
   - Check database credentials in .env files
   - Ensure database names match configuration

3. **Kafka connection errors**
   - Wait for Kafka to fully start (can take 30-60 seconds)
   - Check broker connectivity: `docker-compose logs broker`

4. **JWT token expired**
   - Use the refresh token endpoint to get a new access token
   - Check JWT_EXPIRY_TIME in .env

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation for new features
- Use meaningful commit messages
- Keep services loosely coupled

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI framework for modern Python APIs
- Apache Kafka for event streaming
- PostgreSQL for reliable data storage
- Docker for containerization

## Contact

For questions or support, please open an issue in the repository.

---

**Built with FastAPI, Kafka, and PostgreSQL**
