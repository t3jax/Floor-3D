"""
System Health Check Script
Tests backend, frontend, and database connectivity
"""
import requests
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_backend():
    """Test if backend is running and responsive"""
    try:
        response = requests.get('http://localhost:8000/docs', timeout=5)
        if response.status_code == 200:
            print('✅ Backend is running on http://localhost:8000')
            return True
        else:
            print(f'⚠️  Backend responded with status {response.status_code}')
            return False
    except Exception as e:
        print(f'❌ Backend is not accessible: {e}')
        return False

def test_database():
    """Test database connection"""
    try:
        from app.database_sqlalchemy import SessionLocal, Material
        print('🔄 Testing database connection...')
        
        db = SessionLocal()
        try:
            # Try to query materials
            count = db.query(Material).count()
            print(f'✅ Database connected! Found {count} materials')
            
            # Show sample material
            if count > 0:
                sample = db.query(Material).first()
                print(f'   Sample: {sample.name} - ${sample.cost_per_unit}/{sample.unit}')
            return True
        except Exception as e:
            print(f'❌ Database query failed: {e}')
            return False
        finally:
            db.close()
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

def test_frontend():
    """Test if frontend is running"""
    try:
        response = requests.get('http://localhost:3000', timeout=5)
        if response.status_code == 200:
            print('✅ Frontend is running on http://localhost:3000')
            return True
        else:
            print(f'⚠️  Frontend responded with status {response.status_code}')
            return False
    except Exception as e:
        print(f'❌ Frontend is not accessible: {e}')
        return False

def check_env():
    """Check environment configuration"""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        print('✅ .env file exists')
        with open(env_file) as f:
            content = f.read()
            if 'DATABASE_URL' in content:
                # Mask password
                import re
                url = os.getenv('DATABASE_URL', '')
                masked = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)
                print(f'   DATABASE_URL: {masked}')
                
                # Check if using Supabase or SQLite
                if 'supabase.co' in url:
                    print('   Using: Supabase PostgreSQL ☁️')
                elif 'postgresql://' in url:
                    print('   Using: PostgreSQL')
                else:
                    print('   Using: SQLite (fallback)')
            else:
                print('⚠️  DATABASE_URL not found in .env')
    else:
        print('⚠️  .env file not found')

def main():
    print('='*60)
    print('Floor3D System Health Check')
    print('='*60)
    print()
    
    # Check environment
    check_env()
    print()
    
    # Test components
    backend_ok = test_backend()
    print()
    
    database_ok = test_database()
    print()
    
    frontend_ok = test_frontend()
    print()
    
    # Summary
    print('='*60)
    print('Summary:')
    print('='*60)
    all_ok = backend_ok and database_ok and frontend_ok
    
    if all_ok:
        print('🎉 All systems operational!')
        print()
        print('Next steps:')
        print('1. Open http://localhost:3000 in your browser')
        print('2. Upload a floor plan image')
        print('3. Check Supabase dashboard to verify data storage')
    else:
        print('⚠️  Some components need attention')
        if not backend_ok:
            print('   - Start backend: cd backend && uvicorn app.main:app --reload')
        if not database_ok:
            print('   - Check DATABASE_URL in .env file')
            print('   - Verify Supabase connection string is correct')
        if not frontend_ok:
            print('   - Start frontend: cd frontend && npm start')
    
    print()
    return 0 if all_ok else 1

if __name__ == '__main__':
    exit(main())
