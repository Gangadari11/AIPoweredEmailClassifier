from flask import Flask, render_template_string, request, jsonify
import imaplib
import email
from email.header import decode_header
import ssl
import re
from datetime import datetime
import traceback

app = Flask(__name__)

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Email Classifier</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .form-group { 
            margin-bottom: 15px; 
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="email"], input[type="password"], input[type="text"] { 
            width: 100%; 
            max-width: 400px;
            padding: 10px; 
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        button { 
            background: #007bff; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { 
            background: #0056b3; 
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .loading { 
            display: none; 
            color: #666; 
            margin-top: 15px;
            padding: 10px;
            background: #e3f2fd;
            border-radius: 4px;
        }
        .error { 
            color: #d32f2f; 
            margin-top: 15px;
            padding: 10px;
            background: #ffebee;
            border-radius: 4px;
            border: 1px solid #f8bbd9;
        }
        .success {
            color: #2e7d32;
            margin-top: 15px;
            padding: 10px;
            background: #e8f5e8;
            border-radius: 4px;
        }
        .email-categories { 
            margin-top: 30px; 
        }
        .category { 
            margin-bottom: 25px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .category h3 { 
            background: #f8f9fa; 
            padding: 15px; 
            margin: 0; 
            border-left: 4px solid #007bff;
            color: #333;
        }
        .email-item { 
            border-bottom: 1px solid #eee; 
            padding: 15px; 
            background: #fff; 
        }
        .email-item:last-child {
            border-bottom: none;
        }
        .email-subject { 
            font-weight: bold; 
            color: #333; 
            margin-bottom: 5px;
        }
        .email-sender { 
            color: #666; 
            font-size: 0.9em; 
            margin-bottom: 3px;
        }
        .email-date { 
            color: #999; 
            font-size: 0.8em; 
            margin-bottom: 8px;
        }
        .email-body { 
            color: #555; 
            line-height: 1.4;
        }
        .info-box {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Email Classifier</h1>
        
        <div class="info-box">
            <strong>For Gmail users:</strong> Use an App Password instead of your regular password. 
            Go to Google Account → Security → 2-Step Verification → App passwords.
        </div>
        
        <form id="emailForm">
            <div class="form-group">
                <label for="email">Email Address:</label>
                <input type="email" id="email" name="email" required placeholder="your.email@gmail.com">
            </div>
            
            <div class="form-group">
                <label for="password">Password (App Password for Gmail):</label>
                <input type="password" id="password" name="password" required placeholder="Enter your app password">
            </div>
            
            <div class="form-group">
                <label for="server">IMAP Server:</label>
                <input type="text" id="server" name="server" value="imap.gmail.com" placeholder="imap.gmail.com">
            </div>
            
            <button type="submit" id="submitBtn">🔍 Classify My Emails</button>
        </form>
        
        <div class="loading" id="loading">
            <strong>⏳ Processing...</strong><br>
            Connecting to your email and classifying messages. This may take a moment.
        </div>
        
        <div class="error" id="error" style="display: none;"></div>
        <div class="success" id="success" style="display: none;"></div>
        <div id="results"></div>
    </div>

    <script>
        document.getElementById('emailForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const server = document.getElementById('server').value;
            const submitBtn = document.getElementById('submitBtn');
            
            // Show loading, hide others
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            document.getElementById('success').style.display = 'none';
            document.getElementById('results').innerHTML = '';
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';
            
            try {
                const response = await fetch('/classify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email: email,
                        password: password,
                        server: server
                    })
                });
                
                const data = await response.json();
                
                document.getElementById('loading').style.display = 'none';
                submitBtn.disabled = false;
                submitBtn.textContent = '🔍 Classify My Emails';
                
                if (!response.ok || data.error) {
                    throw new Error(data.error || 'Unknown error occurred');
                }
                
                document.getElementById('success').style.display = 'block';
                document.getElementById('success').innerHTML = `✅ Successfully classified ${data.emails.length} emails!`;
                displayResults(data.emails);
                
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').innerHTML = `❌ <strong>Error:</strong> ${error.message}`;
                submitBtn.disabled = false;
                submitBtn.textContent = '🔍 Classify My Emails';
            }
        });
        
        function displayResults(emails) {
            if (!emails || emails.length === 0) {
                document.getElementById('results').innerHTML = '<p>No emails found.</p>';
                return;
            }
            
            const categories = {};
            
            // Group emails by category
            emails.forEach(email => {
                if (!categories[email.category]) {
                    categories[email.category] = [];
                }
                categories[email.category].push(email);
            });
            
            let html = '<div class="email-categories">';
            
            // Define category icons
            const icons = {
                'work': '💼',
                'personal': '👤',
                'shopping': '🛒',
                'finance': '💰',
                'social': '📱',
                'spam': '🚫',
                'other': '📂'
            };
            
            for (const [category, categoryEmails] of Object.entries(categories)) {
                const icon = icons[category] || '📂';
                html += `<div class="category">
                    <h3>${icon} ${category.toUpperCase()} (${categoryEmails.length} emails)</h3>`;
                
                categoryEmails.forEach(email => {
                    html += `<div class="email-item">
                        <div class="email-subject">${escapeHtml(email.subject || 'No Subject')}</div>
                        <div class="email-sender">From: ${escapeHtml(email.sender || 'Unknown')}</div>
                        <div class="email-date">${escapeHtml(email.date || 'No Date')}</div>
                        <div class="email-body">${escapeHtml(email.body || 'No content preview available')}</div>
                    </div>`;
                });
                
                html += '</div>';
            }
            
            html += '</div>';
            document.getElementById('results').innerHTML = html;
        }
        
        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, function(m) { return map[m]; });
        }
    </script>
</body>
</html>
"""

class EmailClassifier:
    def __init__(self):
        # Enhanced keyword-based classifier
        self.categories = {
            'work': ['meeting', 'project', 'deadline', 'report', 'task', 'office', 'colleague', 'conference', 'team', 'manager', 'client', 'proposal', 'contract'],
            'personal': ['family', 'friend', 'birthday', 'vacation', 'personal', 'home', 'weekend', 'dinner', 'party', 'wedding'],
            'shopping': ['order', 'purchase', 'cart', 'sale', 'discount', 'shipping', 'delivery', 'amazon', 'ebay', 'store', 'receipt', 'confirmation'],
            'finance': ['bank', 'payment', 'invoice', 'bill', 'account', 'transaction', 'credit', 'statement', 'balance', 'loan', 'mortgage'],
            'social': ['facebook', 'twitter', 'instagram', 'linkedin', 'notification', 'like', 'comment', 'share', 'follow', 'post'],
            'spam': ['win', 'lottery', 'free', 'urgent', 'click here', 'limited time', 'offer', 'congratulations', 'prize', 'winner']
        }
    
    def classify_email(self, subject, body):
        text = ((subject or '') + " " + (body or '')).lower()
        scores = {}
        
        for category, keywords in self.categories.items():
            score = sum(1 for keyword in keywords if keyword in text)
            scores[category] = score
        
        # Return category with highest score, or 'other' if no match
        if max(scores.values()) == 0:
            return 'other'
        return max(scores, key=scores.get)

class EmailFetcher:
    def __init__(self):
        self.classifier = EmailClassifier()
    
    def connect_to_email(self, email_address, password, imap_server="imap.gmail.com"):
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to server
            mail = imaplib.IMAP4_SSL(imap_server, 993, ssl_context=context)
            mail.login(email_address, password)
            return mail
        except imaplib.IMAP4.error as e:
            raise Exception(f"IMAP authentication failed. Please check your email and password. For Gmail, use an App Password: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to connect to email server: {str(e)}")
    
    def fetch_emails(self, mail, num_emails=30):
        try:
            mail.select('inbox')
            
            # Search for all emails
            status, messages = mail.search(None, 'ALL')
            if status != 'OK':
                raise Exception("Failed to search emails")
            
            email_ids = messages[0].split()
            if not email_ids:
                return []
            
            # Get recent emails
            recent_emails = email_ids[-num_emails:] if len(email_ids) > num_emails else email_ids
            
            emails = []
            for email_id in reversed(recent_emails):  # Most recent first
                try:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK' or not msg_data or not msg_data[0]:
                        continue
                        
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract email details
                    subject = self.decode_mime_words(msg.get('Subject', ''))
                    sender = msg.get('From', '')
                    date = msg.get('Date', '')
                    
                    # Extract body
                    body = self.extract_body(msg)
                    
                    # Classify email
                    category = self.classifier.classify_email(subject, body)
                    
                    emails.append({
                        'id': email_id.decode(),
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'body': body[:300] + '...' if len(body) > 300 else body,
                        'category': category
                    })
                except Exception as e:
                    print(f"Error processing email {email_id}: {e}")
                    continue
            
            return emails
        except Exception as e:
            raise Exception(f"Failed to fetch emails: {str(e)}")
    
    def decode_mime_words(self, s):
        if s is None:
            return ''
        try:
            decoded_parts = decode_header(s)
            decoded_string = ''
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    decoded_string += str(part)
            return decoded_string
        except Exception:
            return str(s) if s else ''
    
    def extract_body(self, msg):
        body = ""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                                break
                        except Exception:
                            continue
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                except Exception:
                    body = ""
            
            # Clean up body
            body = re.sub(r'\s+', ' ', body.strip())
            return body
        except Exception:
            return ""

# Initialize email fetcher
email_fetcher = EmailFetcher()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/classify', methods=['POST'])
def classify_emails():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        email_address = data.get('email', '').strip()
        password = data.get('password', '').strip()
        server = data.get('server', 'imap.gmail.com').strip()
        
        if not email_address or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        print(f"Attempting to connect to {server} with email: {email_address}")
        
        # Connect to email
        mail = email_fetcher.connect_to_email(email_address, password, server)
        print("Successfully connected to email server")
        
        # Fetch and classify emails
        emails = email_fetcher.fetch_emails(mail, num_emails=30)
        print(f"Successfully fetched {len(emails)} emails")
        
        # Close connection
        try:
            mail.close()
            mail.logout()
        except:
            pass  # Ignore close errors
        
        return jsonify({'emails': emails})
        
    except Exception as e:
        print(f"Error in classify_emails: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Email Classifier App...")
    print("Access the app at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)