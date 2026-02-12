def get_otp_template(name: str, otp: str) -> dict:
    html_content = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kode Verifikasi Reset Password</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background-color: #f5f5f5;
                line-height: 1.6;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px 20px;
                text-align: center;
            }}
            .header h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .greeting {{
                font-size: 18px;
                color: #333333;
                margin-bottom: 20px;
            }}
            .message {{
                font-size: 16px;
                color: #555555;
                margin-bottom: 30px;
            }}
            .otp-box {{
                background-color: #f8f9fa;
                border: 2px dashed #667eea;
                border-radius: 12px;
                padding: 30px;
                text-align: center;
                margin: 30px 0;
            }}
            .otp-label {{
                font-size: 14px;
                color: #666666;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .otp-code {{
                font-size: 36px;
                font-weight: 700;
                color: #667eea;
                letter-spacing: 8px;
                font-family: 'Courier New', monospace;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .warning-text {{
                font-size: 14px;
                color: #856404;
                margin: 0;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 30px;
                text-align: center;
                border-top: 1px solid #e9ecef;
            }}
            .footer-text {{
                font-size: 13px;
                color: #6c757d;
                margin: 5px 0;
            }}
            @media only screen and (max-width: 600px) {{
                .content {{
                    padding: 30px 20px;
                }}
                .header h1 {{
                    font-size: 24px;
                }}
                .otp-code {{
                    font-size: 28px;
                    letter-spacing: 4px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>Verifikasi Keamanan</h1>
            </div>
            
            <div class="content">
                <p class="greeting">Halo <strong>{name}</strong>,</p>
                
                <p class="message">
                    Kami menerima permintaan untuk mereset password akun SIPA Anda. 
                    Gunakan kode OTP di bawah ini untuk melanjutkan proses reset password.
                </p>
                
                <div class="otp-box">
                    <div class="otp-label">Kode Verifikasi Anda</div>
                    <div class="otp-code">{otp}</div>
                </div>
                
                <div class="warning">
                    <p class="warning-text">
                        <strong>Penting:</strong> Kode ini hanya berlaku selama 5 menit. 
                        Jangan berikan kode ini kepada siapa pun, termasuk karyawan pengelola SIPA.
                    </p>
                </div>
                
                <p class="message">
                    Jika Anda tidak melakukan permintaan ini, abaikan email ini atau 
                    hubungi admin segera.
                </p>
            </div>
            
            <div class="footer">
                <p class="footer-text">Email ini dikirim secara otomatis, mohon tidak membalas.</p>
                <p class="footer-text">© 2025 SIPA. Hak cipta dilindungi.</p>
            </div>
        </div>
    </body>
    </html>
    """

    plain_text = (
        f"Halo {name},\n\n"
        f"Kami menerima permintaan untuk mereset password akun SIPA Anda.\n"
        f"Gunakan kode OTP berikut: {otp}\n\n"
        f"Kode ini hanya berlaku selama 5 menit. Jangan berikan kode ini kepada siapa pun.\n\n"
        f"Jika Anda tidak melakukan permintaan ini, abaikan email ini."
    )

    return {
        "subject": "Kode Verifikasi Reset Password - SIPA",
        "html_content": html_content,
        "plain_content": plain_text,
    }


def get_login_alert_template(name: str, time_str: str, device_name: str, city: str) -> dict:
    html_content = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Peringatan Keamanan Login</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background-color: #f5f5f5;
                line-height: 1.6;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
            }}
            .header {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 40px 20px;
                text-align: center;
            }}
            .header h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .alert-badge {{
                background-color: #dc3545;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                display: inline-block;
                margin-top: 10px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .greeting {{
                font-size: 18px;
                color: #333333;
                margin-bottom: 20px;
            }}
            .message {{
                font-size: 16px;
                color: #555555;
                margin-bottom: 25px;
            }}
            .info-box {{
                background-color: #e7f3ff;
                border-left: 4px solid #2196F3;
                padding: 20px;
                margin: 25px 0;
                border-radius: 4px;
            }}
            .info-row {{
                display: flex;
                margin: 10px 0;
                font-size: 15px;
            }}
            .info-label {{
                font-weight: 600;
                color: #1976D2;
                min-width: 120px;
            }}
            .info-value {{
                color: #333333;
                word-break: break-all;
            }}
            .action-box {{
                background-color: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 8px;
                padding: 20px;
                margin: 25px 0;
                text-align: center;
            }}
            .action-text {{
                font-size: 15px;
                color: #856404;
                margin-bottom: 15px;
            }}
            .button {{
                display: inline-block;
                background-color: #dc3545;
                color: #ffffff;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                margin-top: 10px;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 30px;
                text-align: center;
                border-top: 1px solid #e9ecef;
            }}
            .footer-text {{
                font-size: 13px;
                color: #6c757d;
                margin: 5px 0;
            }}
            @media only screen and (max-width: 600px) {{
                .content {{
                    padding: 30px 20px;
                }}
                .header h1 {{
                    font-size: 24px;
                }}
                .info-row {{
                    flex-direction: column;
                }}
                .info-label {{
                    margin-bottom: 5px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>Peringatan Keamanan</h1>
                <div class="alert-badge">Login Baru Terdeteksi</div>
            </div>
            
            <div class="content">
                <p class="greeting">Halo <strong>{name}</strong>,</p>
                
                <p class="message">
                    Kami mendeteksi aktivitas login baru pada akun SIPA Anda. 
                    Jika ini adalah Anda, tidak ada tindakan yang diperlukan.
                </p>
                
                <div class="info-box">
                    <div class="info-row">
                        <div class="info-label">Waktu Login:</div>
                        <div class="info-value">{time_str} WIB</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Perangkat:</div>
                        <div class="info-value">{device_name}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Lokasi:</div>
                        <div class="info-value">{city} (Sekitar)</div>
                    </div>
                </div>
                
                <div class="action-box">
                    <p class="action-text">
                        <strong>⚠️Bukan Anda?</strong><br>
                        Jika Anda tidak mengenali aktivitas ini, segera amankan akun Anda.
                    </p>
                </div>
            </div>
            
            <div class="footer">
                <p class="footer-text">Email ini dikirim secara otomatis, mohon tidak membalas.</p>
                <p class="footer-text">© 2025 SIPA. Hak cipta dilindungi.</p>
            </div>
        </div>
    </body>
    </html>
    """

    plain_text = (
        f"Halo {name},\n\n"
        f"PERINGATAN KEAMANAN: Login Baru Terdeteksi\n\n"
        f"Akun Anda baru saja login pada {time_str} WIB.\n"
        f"Perangkat: {device_name}\n"
        f"Lokasi: {city} (Sekitar)\n\n"
        f"Jika ini bukan Anda, harap segera hubungi admin atau reset password Anda.\n\n"
        f"Untuk keamanan akun, gunakan password yang kuat dan aktifkan autentikasi dua faktor."
    )

    return {
        "subject": "Peringatan Keamanan: Login Baru Terdeteksi - SIPA",
        "html_content": html_content,
        "plain_content": plain_text,
    }


def get_password_reset_success_template(name: str, time_str: str) -> dict:
    html_content = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Password Berhasil Diubah</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background-color: #f5f5f5;
                line-height: 1.6;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
            }}
            .header {{
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                padding: 40px 20px;
                text-align: center;
            }}
            .header h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .greeting {{
                font-size: 18px;
                color: #333333;
                margin-bottom: 20px;
            }}
            .message {{
                font-size: 16px;
                color: #555555;
                margin-bottom: 25px;
            }}
            .info-box {{
                background-color: #d4edda;
                border-left: 4px solid #28a745;
                padding: 20px;
                margin: 25px 0;
                border-radius: 4px;
            }}
            .action-text {{
                font-size: 15px;
                color: #155724;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 30px;
                text-align: center;
                border-top: 1px solid #e9ecef;
            }}
            .footer-text {{
                font-size: 13px;
                color: #6c757d;
                margin: 5px 0;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>Password Berhasil Diubah</h1>
            </div>
            
            <div class="content">
                <p class="greeting">Halo <strong>{name}</strong>,</p>
                
                <p class="message">
                    Password akun SIPA Anda telah berhasil diperbarui pada <strong>{time_str} WIB</strong>.
                    Anda sekarang dapat login menggunakan password baru Anda.
                </p>
                
                <div class="info-box">
                    <p class="action-text">
                        <strong>⚠️ Bukan Anda?</strong><br>
                        Jika Anda tidak melakukan perubahan ini, akun Anda mungkin telah disusupi. 
                        Segera hubungi administrator sistem.
                    </p>
                </div>
            </div>
            
            <div class="footer">
                <p class="footer-text">Email ini dikirim secara otomatis, mohon tidak membalas.</p>
                <p class="footer-text">© 2025 SIPA. Hak cipta dilindungi.</p>
            </div>
        </div>
    </body>
    </html>
    """

    plain_text = (
        f"Halo {name},\n\n"
        f"Password akun SIPA Anda telah berhasil diperbarui pada {time_str} WIB.\n\n"
        f"Jika Anda tidak melakukan perubahan ini, segera hubungi administrator karena keamanan akun Anda mungkin terancam."
    )

    return {
        "subject": "Notifikasi Perubahan Password - SIPA",
        "html_content": html_content,
        "plain_content": plain_text,
    }
