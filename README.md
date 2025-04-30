# HumanTyped API

A delightfully pedantic API for verifying that your typing was indeed performed by a human and not some silicon-based impostor.

## What's All This Then?

HumanTyped API is a Flask-based service that meticulously records and analyzes keypress patterns to verify the authenticity of human typing. Because in a world where AI can write sonnets, we're reduced to proving our humanity through typing speed inconsistencies. How terribly quaint.

## Features

- **Keypress Recording**: Captures each keystroke with timestamp precision that would make an atomic clock blush
- **Typing Analysis**: Calculates typing speed with mathematical certainty (give or take the occasional quantum fluctuation)
- **Document Management**: Creates and stores documents with all the diligence of a particularly attentive librarian
- **Verification Endpoints**: Provides irrefutable proof that you, a human, did indeed type those words in that particular order

## Installation

First, ensure you have Python installed. If not, I'm rather impressed you've made it this far in life as a developer.

```bash
# Clone the repository (one assumes you have git installed, otherwise things are about to get awkward)
git clone https://github.com/yourusername/humantyped-api.git

# Navigate to the project directory
cd humantyped-api

# Install dependencies (a rather polite way of saying "download half the internet")
pip install -r requirements.txt
```

## Database Setup

The API requires PostgreSQL, that most reliable of database systems. Create a database and set up the following tables:

```sql
-- One imagines you know how to create a database in PostgreSQL
-- If not, perhaps consider a career in interpretive dance

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    title VARCHAR(255) DEFAULT 'Untitled Document',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_characters INTEGER DEFAULT 0
);

CREATE TABLE key_presses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    key_char VARCHAR(1) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    typing_speed NUMERIC(10, 2) DEFAULT 0
);

-- Function to calculate typing speed
CREATE OR REPLACE FUNCTION record_keypress(doc_id UUID, key_character VARCHAR)
RETURNS UUID AS $$
DECLARE
    new_id UUID;
    char_count INTEGER;
    time_diff NUMERIC;
    typing_speed NUMERIC;
    last_press TIMESTAMP;
BEGIN
    -- Get the count of existing keypresses
    SELECT COUNT(*) INTO char_count FROM key_presses WHERE document_id = doc_id;
    
    -- Get the timestamp of the last keypress
    SELECT created_at INTO last_press FROM key_presses 
    WHERE document_id = doc_id 
    ORDER BY created_at DESC 
    LIMIT 1;
    
    -- Calculate typing speed (characters per minute)
    IF last_press IS NOT NULL THEN
        time_diff := EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_press));
        typing_speed := CASE 
            WHEN time_diff > 0 THEN (60 / time_diff)
            ELSE 0
        END;
    ELSE
        typing_speed := 0;
    END IF;
    
    -- Insert the new keypress
    INSERT INTO key_presses (document_id, key_char, typing_speed)
    VALUES (doc_id, key_character, typing_speed)
    RETURNING id INTO new_id;
    
    -- Update the document's character count
    UPDATE documents SET total_characters = char_count + 1 WHERE id = doc_id;
    
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get verification data
CREATE OR REPLACE FUNCTION get_verification_data(doc_id UUID)
RETURNS TABLE (
    created_at TIMESTAMP,
    key_char VARCHAR,
    typing_speed NUMERIC,
    total_characters INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kp.created_at,
        kp.key_char,
        kp.typing_speed,
        ROW_NUMBER() OVER (ORDER BY kp.created_at)::INTEGER as total_characters
    FROM key_presses kp
    WHERE kp.document_id = doc_id
    ORDER BY kp.created_at;
END;
$$ LANGUAGE plpgsql;
```

## Configuration

Create a `.env` file in the project root. Do try to keep it secret, won't you? We're not running a public library here.

```
DB_NAME=typing_verification
DB_USER=your_username
DB_PASSWORD=your_password_that_is_definitely_not_password123
DB_HOST=localhost
DB_PORT=5432
```

## Running the Service

For development (when bugs are expected and indeed welcomed as old friends):

```bash
python app.py
```

For production (when one hopes the bugs have been politely asked to leave):

```bash
gunicorn -c gunicorn_config.py app:app
```

The service will be available at:
- Development: http://localhost:5000
- Production: http://localhost:8080

## API Endpoints

### Health Check
```
GET /api/health
```
Returns a status of "healthy" if the service is running. If not, well, you won't get a response, will you? Rather self-explanatory, that.

### Create Document
```
POST /api/documents
```
Creates a new document to track typing for. Returns a document ID that you'll need for subsequent calls. Do make a note of it, there won't be a pop quiz, but you'll feel rather silly if you lose it.

### Record Keypress
```
POST /api/keypress
```
Records a single keypress with timestamp and calculates typing speed. The API's equivalent of watching over your shoulder, but with less awkward breathing.

### Submit Document
```
POST /api/submit
```
Finalizes a document and provides verification statistics. The moment of truth, as it were.

### Verify Document
```
GET /api/verify/<document_id>
```
Retrieves the complete typing verification data. Prepare to have your humanity judged by an algorithm. How the tables have turned.

## Dependencies

This project relies on a carefully curated collection of Python packages:

- Flask: For serving the API with British reserve and efficiency
- PostgreSQL: For storing data with a stiff upper lip
- Gunicorn: For production deployment that doesn't crack under pressure
- Various other bits and bobs listed in `requirements.txt`

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Tea and biscuits not provided, but highly recommended during code reviews.

## License

[MIT](https://choosealicense.com/licenses/mit/) - Because we're not monsters.
