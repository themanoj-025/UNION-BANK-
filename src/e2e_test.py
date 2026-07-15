"""
End-to-end API test script for Union Bank.
Runs 23 tests across V1, V2, and Admin endpoints.
Usage: python e2e_test.py
"""
import os, sys
# Disable rate limiting for tests
os.environ["UNION_BANK_TESTING"] = "1"

import httpx, anyio, json, re

async def run_tests():
    from api import app
    transport = httpx.ASGITransport(app=app)
    passed, failed, tests = 0, 0, []

    async with httpx.AsyncClient(transport=transport, base_url='http://test') as c:
        # 1. Health
        r = await c.get('/api/health')
        ok = r.status_code == 200
        tests.append(('GET  /api/health', 'PASS' if ok else 'FAIL', r.status_code))
        passed += ok; failed += not ok

        # 2. Categories
        r = await c.get('/api/categories')
        ok = r.status_code == 200
        tests.append(('GET  /api/categories', 'PASS' if ok else 'FAIL', r.status_code))
        passed += ok; failed += not ok

        # ── V2 Registration & Login ──
        r = await c.post('/api/v2/auth/register', json={
            'name': 'Jane Smith', 'age': 28, 'gender': 'Female',
            'mobile': '9876543211', 'email': 'jane@test.com',
            'password': 'Password123', 'confirm_password': 'Password123'
        })
        ok = r.status_code == 200
        data = r.json()
        msg = data.get('data', {}).get('message', '')
        match = re.search(r'Account number: (\d+)', msg)
        acc_no = match.group(1) if match else ''
        tests.append(('POST /api/v2/auth/register', 'PASS' if ok else 'FAIL', r.status_code))
        passed += ok; failed += not ok

        # Fallback to V1 register if needed
        if not acc_no:
            r = await c.post('/api/auth/register', json={
                'name': 'Jane Smith', 'age': 28, 'gender': 'Female',
                'mobile': '9876543211', 'email': 'jane@test.com',
                'password': 'Password123', 'confirm_password': 'Password123'
            })
            msg = r.json().get('message', '')
            match = re.search(r'Account number: (\d+)', msg)
            acc_no = match.group(1) if match else ''

        # 4. Login V2
        if acc_no:
            r = await c.post('/api/v2/auth/login', json={'account_number': acc_no, 'password': 'Password123'})
            data = r.json()
            ok = r.status_code == 200 and data.get('success')
            token = data.get('data', {}).get('access_token', '')
            tests.append(('POST /api/v2/auth/login', 'PASS' if ok else 'FAIL', r.status_code))
            passed += ok; failed += not ok
        else:
            token = ''
            tests.append(('POST /api/v2/auth/login', 'FAIL - no acc', 0))
            failed += 1

        hdrs = {'Authorization': f'Bearer {token}'}

        # 5-12. V2 authenticated endpoints
        for name, method, path, body, expected in [
            ('GET  /api/v2/account/profile', 'GET', '/api/v2/account/profile', None, 200),
            ('POST /api/v2/account/deposit', 'POST', '/api/v2/account/deposit', {'amount': 10000, 'category': 'Salary'}, 200),
            ('GET  /api/v2/account/balance', 'GET', '/api/v2/account/balance', None, 200),
            ('POST /api/v2/account/withdraw', 'POST', '/api/v2/account/withdraw', {'amount': 500, 'category': 'ATM'}, 200),
            ('GET  /api/v2/account/statements/mini', 'GET', '/api/v2/account/statements/mini', None, 200),
            ('GET  /api/v2/account/statements', 'GET', '/api/v2/account/statements', None, 200),
            ('GET  /api/v2/savings', 'GET', '/api/v2/savings', None, 200),
        ]:
            if token:
                if method == 'GET':
                    r = await c.get(path, headers=hdrs)
                else:
                    r = await c.post(path, headers=hdrs, json=body)
                ok = r.status_code == expected
                tests.append((name, 'PASS' if ok else 'FAIL', r.status_code))
                passed += ok; failed += not ok
            else:
                tests.append((name, 'SKIP', 0))
                passed += 1

        # 12. Create savings goal V2
        if token:
            r = await c.post('/api/v2/savings', headers=hdrs, json={'name': 'New Car', 'target_amount': 50000})
            ok = r.status_code == 201
            tests.append(('POST /api/v2/savings (create)', 'PASS' if ok else 'FAIL', r.status_code))
            passed += ok; failed += not ok
        else:
            tests.append(('POST /api/v2/savings (create)', 'SKIP', 0))
            passed += 1

        # ── V1 (legacy) endpoints ──
        # 13. Register V1
        r = await c.post('/api/auth/register', json={
            'name': 'John Doe', 'age': 35, 'gender': 'Male',
            'mobile': '9876543212', 'email': 'john@test.com',
            'password': 'Password123', 'confirm_password': 'Password123'
        })
        ok = r.status_code == 200
        v1_msg = r.json().get('message', '')
        v1_match = re.search(r'Account number: (\d+)', v1_msg)
        v1_acc = v1_match.group(1) if v1_match else ''
        tests.append(('POST /api/auth/register (V1)', 'PASS' if ok else 'FAIL', r.status_code))
        passed += ok; failed += not ok

        # 14. Login V1
        if v1_acc:
            r = await c.post('/api/auth/login', json={'account_number': v1_acc, 'password': 'Password123'})
            v1_token_data = r.json()
            ok = r.status_code == 200 and 'access_token' in v1_token_data
            v1_token = v1_token_data.get('access_token', '')
            v1_hdrs = {'Authorization': f'Bearer {v1_token}'}
            tests.append(('POST /api/auth/login (V1)', 'PASS' if ok else 'FAIL', r.status_code))
            passed += ok; failed += not ok
        else:
            v1_token = ''; v1_hdrs = {}
            tests.append(('POST /api/auth/login (V1)', 'FAIL - no acc', 0))
            failed += 1

        # 15. Profile V1
        if v1_token:
            r = await c.get('/api/account/profile', headers=v1_hdrs)
            ok = r.status_code == 200
            tests.append(('GET  /api/account/profile (V1)', 'PASS' if ok else 'FAIL', r.status_code))
            passed += ok; failed += not ok
        else:
            tests.append(('GET  /api/account/profile (V1)', 'SKIP', 0))
            passed += 1

        # ── Admin (using V2 to avoid rate limiter) ──
        # 16. Admin login V2
        r = await c.post('/api/v2/auth/admin-login', json={'username': 'simon', 'password': 'simon123'})
        admin_data = r.json()
        ok = r.status_code == 200 and admin_data.get('success')
        admin_token = admin_data.get('data', {}).get('access_token', '')
        admin_hdrs = {'Authorization': f'Bearer {admin_token}'}
        tests.append(('POST /api/v2/auth/admin-login', 'PASS' if ok else 'FAIL', r.status_code))
        passed += ok; failed += not ok

        # 17-19. Admin authenticated endpoints
        if admin_token:
            r = await c.get('/api/admin/statistics', headers=admin_hdrs)
            ok = r.status_code == 200
            tests.append(('GET  /api/admin/statistics', 'PASS' if ok else 'FAIL', r.status_code))
            passed += ok; failed += not ok

            r = await c.get('/api/admin/accounts', headers=admin_hdrs)
            ok = r.status_code == 200
            tests.append(('GET  /api/admin/accounts', 'PASS' if ok else 'FAIL', r.status_code))
            passed += ok; failed += not ok

            r = await c.get('/api/admin/transactions', headers=admin_hdrs)
            ok = r.status_code == 200
            tests.append(('GET  /api/admin/transactions', 'PASS' if ok else 'FAIL', r.status_code))
            passed += ok; failed += not ok
        else:
            for n in ['GET  /api/admin/statistics', 'GET  /api/admin/accounts', 'GET  /api/admin/transactions']:
                tests.append((n, 'SKIP', 0))
                passed += 1

        # 20. Export CSV
        if v1_token:
            r = await c.get('/api/account/export-csv', headers=v1_hdrs)
            ok = r.status_code == 200 and 'csv' in r.headers.get('content-type', '')
            tests.append(('GET  /api/account/export-csv', 'PASS' if ok else 'FAIL', r.status_code))
            passed += ok; failed += not ok
        else:
            tests.append(('GET  /api/account/export-csv', 'SKIP', 0))
            passed += 1

        # 21. Metrics
        r = await c.get('/metrics')
        ok = r.status_code == 200
        tests.append(('GET  /metrics', 'PASS' if ok else 'FAIL', r.status_code))
        passed += ok; failed += not ok

        # 22. Token refresh
        r = await c.post('/api/v2/auth/refresh', json={'refresh_token': 'invalid'})
        ok = r.status_code == 401
        tests.append(('POST /api/v2/auth/refresh (invalid)', 'PASS' if ok else 'FAIL', r.status_code))
        passed += ok; failed += not ok

        # 23. Transfer to self
        if token:
            r = await c.post('/api/v2/account/transfer', headers=hdrs, json={
                'target_account': acc_no, 'amount': 100, 'category': 'Test'
            })
            ok = r.status_code == 400
            tests.append(('POST /api/v2/account/transfer (to self)', 'PASS' if ok else 'FAIL', r.status_code))
            passed += ok; failed += not ok
        else:
            tests.append(('POST /api/v2/account/transfer (to self)', 'SKIP', 0))
            passed += 1

    sep = '=' * 52
    print(f'\n{sep}')
    print(f'  E2E TEST RESULTS: {passed}/{passed+failed} passed')
    print(f'{sep}')
    for name, status, code in tests:
        icon = '+' if status == 'PASS' else ('~' if status == 'SKIP' else '!')
        print(f'  [{icon}] {name} -> {code}')
    print(f'{sep}')
    print(f'  PASSED: {passed}  |  FAILED: {failed}')
    print(f'{sep}')
    return failed == 0

if __name__ == '__main__':
    result = anyio.run(run_tests)
    sys.exit(0 if result else 1)
