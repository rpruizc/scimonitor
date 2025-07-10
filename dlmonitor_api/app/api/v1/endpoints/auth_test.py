"""
Temporary authentication testing endpoints.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.base import get_async_session
from app.core.settings import settings
from app.models.user import UserModel
from app.core.auth import verify_supabase_token

logger = structlog.get_logger()
router = APIRouter()


@router.get("/auth/github", summary="GitHub OAuth redirect")
async def github_auth():
    """
    Redirect to GitHub OAuth via Supabase.
    """
    # Try without redirect_to first to see if it uses the configured site URL
    redirect_url = f"{settings.supabase_url}/auth/v1/authorize?provider=github"
    return RedirectResponse(url=redirect_url)


@router.get("/auth/simple-test", summary="Simple OAuth test page", response_class=HTMLResponse)
async def simple_auth_test():
    """
    Provide a simple HTML page for OAuth testing.
    """
    # Build the JavaScript separately to avoid f-string issues
    js_code = """
        let supabaseClient = null;
        
        // Initialize with debugging
        try {
            console.log('Initializing Supabase client...');
            console.log('URL:', '""" + settings.supabase_url + """');
            console.log('Key:', '""" + settings.supabase_anon_key[:20] + """...');
            
            // Check if Supabase is loaded
            if (typeof supabase === 'undefined') {
                document.getElementById('debug-info').innerHTML = '❌ Supabase library not loaded';
                throw new Error('Supabase library not loaded');
            }
            
            supabaseClient = supabase.createClient(
                '""" + settings.supabase_url + """',
                '""" + settings.supabase_anon_key + """'
            );
            
            document.getElementById('debug-info').innerHTML = '✅ Supabase client created successfully';
            console.log('Supabase client created:', supabaseClient);
            
            // Check for existing session
            supabaseClient.auth.getSession().then(({data, error}) => {
                console.log('Session check:', data, error);
                if (data.session) {
                    showLoggedIn(data.session);
                }
            });
            
        } catch (error) {
            console.error('Supabase initialization error:', error);
            document.getElementById('debug-info').innerHTML = '❌ Error: ' + error.message;
        }
        
        function testConnection() {
            document.getElementById('status').innerHTML = 'Testing connection...';
            if (supabaseClient) {
                console.log('Supabase client is ready');
                document.getElementById('status').innerHTML = '✅ Supabase client ready';
            } else {
                document.getElementById('status').innerHTML = '❌ Supabase client not initialized';
            }
        }
        
        async function signInWithGitHub() {
            try {
                document.getElementById('status').innerHTML = 'Starting GitHub login...';
                console.log('Starting GitHub OAuth...');
                
                if (!supabaseClient) {
                    throw new Error('Supabase client not initialized');
                }
                
                const {data, error} = await supabaseClient.auth.signInWithOAuth({
                    provider: 'github',
                    options: {
                        redirectTo: 'http://localhost:8000/api/v1/auth/simple-test'
                    }
                });
                
                console.log('OAuth response:', data, error);
                
                if (error) {
                    document.getElementById('status').innerHTML = 'Error: ' + error.message;
                    console.error('OAuth error:', error);
                } else {
                    document.getElementById('status').innerHTML = 'Redirecting to GitHub...';
                }
            } catch (error) {
                console.error('Sign in error:', error);
                document.getElementById('status').innerHTML = 'Error: ' + error.message;
            }
        }
        
        async function signOut() {
            try {
                if (supabaseClient) {
                    await supabaseClient.auth.signOut();
                    document.getElementById('status').innerHTML = 'Signed out';
                    document.getElementById('user-info').innerHTML = '';
                    document.getElementById('token-info').innerHTML = '';
                }
            } catch (error) {
                console.error('Sign out error:', error);
            }
        }
        
        function showLoggedIn(session) {
            document.getElementById('status').innerHTML = '✅ Logged in!';
            document.getElementById('user-info').innerHTML = '<h3>User Info:</h3><pre>' + JSON.stringify(session.user, null, 2) + '</pre>';
            document.getElementById('token-info').innerHTML = 
                '<h3>🎉 Access Token (copy this):</h3>' +
                '<textarea style="width:100%; height:100px;">' + session.access_token + '</textarea>' +
                '<br><br>' +
                '<h3>Test with curl:</h3>' +
                '<code>curl -H "Authorization: Bearer ' + session.access_token + '" http://localhost:8000/api/v1/users/me</code>';
        }
        
        // Listen for auth changes
        if (supabaseClient) {
            supabaseClient.auth.onAuthStateChange((event, session) => {
                console.log('Auth state change:', event, session);
                if (session) {
                    showLoggedIn(session);
                }
            });
        }
    """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>DLMonitor Auth Test</title>
        <script src="https://unpkg.com/@supabase/supabase-js@2"></script>
    </head>
    <body>
        <h1>🔐 DLMonitor Authentication Test</h1>
        <div id="status">Not logged in</div>
        <div id="debug-info" style="background: #f0f0f0; padding: 10px; margin: 10px 0;"></div>
        <br>
        <button onclick="testConnection()">Test Connection</button>
        <button onclick="signInWithGitHub()">Sign in with GitHub</button>
        <button onclick="signOut()">Sign Out</button>
        <br><br>
        <div id="user-info"></div>
        <div id="token-info"></div>
        
        <script>
            {js_code}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/auth/callback", summary="OAuth callback handler")
async def auth_callback(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Handle OAuth callback and extract user info.
    """
    try:
        # Get query parameters
        params = dict(request.query_params)
        
        # Get the full URL for debugging (tokens might be in fragment)
        full_url = str(request.url)
        
        # Check for access_token in various places
        access_token = None
        
        # Method 1: Query parameters
        if "access_token" in params:
            access_token = params["access_token"]
            logger.info("Found access_token in query parameters")
        
        # Method 2: Check for code parameter (authorization code flow)
        elif "code" in params:
            code = params["code"]
            logger.info("Found authorization code", code=code[:20] + "...")
            
            # Exchange code for token using Supabase
            try:
                from supabase import create_client
                supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
                
                # This should exchange the code for tokens
                auth_response = supabase.auth.exchange_code_for_session({"auth_code": code})
                
                if auth_response and hasattr(auth_response, 'session') and auth_response.session:
                    access_token = auth_response.session.access_token
                    logger.info("Successfully exchanged code for access_token")
                else:
                    logger.error("Failed to exchange code for session")
                    
            except Exception as e:
                logger.error("Code exchange failed", error=str(e))
        
        if access_token:
            # Verify token with Supabase
            try:
                user_data = await verify_supabase_token(access_token)
                
                if user_data:
                    # Create or update user in our database
                    user = await create_or_update_user(session, user_data, access_token)
                    
                    return JSONResponse({
                        "message": "🎉 Authentication successful!",
                        "access_token": access_token,
                        "user": user.to_dict(),
                        "instructions": {
                            "step_1": "Copy the access_token above",
                            "step_2": f"curl -H \"Authorization: Bearer {access_token}\" http://localhost:8000/api/v1/users/me",
                            "step_3": "Test other protected endpoints with this token"
                        }
                    })
                else:
                    raise HTTPException(status_code=401, detail="Invalid token")
                    
            except Exception as e:
                logger.error("Token verification failed", error=str(e))
                raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
        
        elif "error" in params:
            return JSONResponse({
                "error": f"OAuth error: {params['error']}",
                "error_description": params.get("error_description", ""),
                "params": params,
                "troubleshooting": {
                    "issue": "OAuth error from Supabase",
                    "check": "Verify GitHub OAuth app configuration in Supabase dashboard"
                }
            })
        
        else:
            # Debug response - show what we received
            return JSONResponse({
                "message": "🔍 OAuth callback debugging info",
                "query_params": params,
                "full_url": full_url,
                "troubleshooting": {
                    "issue": "No access_token or code found",
                    "possible_causes": [
                        "Redirect URL not configured in Supabase dashboard",
                        "GitHub OAuth app not properly configured",
                        "Token might be in URL fragment (check browser developer tools)",
                        "Need to configure redirect URL in Supabase: Authentication > URL Configuration"
                    ],
                    "alternative": "Try the simple test page: http://localhost:8000/api/v1/auth/simple-test"
                }
            })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Callback handling failed", error=str(e))
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/auth/test-token", summary="Test JWT token")
async def test_token(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Test a JWT token manually.
    Send POST with {"token": "your-jwt-token"}
    """
    try:
        body = await request.json()
        token = body.get("token")
        
        if not token:
            raise HTTPException(status_code=400, detail="Token required in request body")
        
        # Verify token
        user_data = await verify_supabase_token(token)
        
        if user_data:
            # Create or update user
            user = await create_or_update_user(session, user_data, token)
            
            return {
                "message": "Token valid!",
                "user_data": user_data,
                "database_user": user.to_dict()
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token test failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Token test failed: {str(e)}")


async def create_or_update_user(session: AsyncSession, user_data: dict, access_token: str) -> UserModel:
    """Create or update user in our database."""
    from sqlalchemy import select
    
    supabase_id = user_data.get("sub")
    email = user_data.get("email")
    
    # Check if user exists
    result = await session.execute(
        select(UserModel).where(UserModel.supabase_id == supabase_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update existing user
        user.email = email
        user.email_confirmed = user_data.get("email_confirmed", False)
        user.update_last_login()
        
        # Update GitHub info if available
        user_metadata = user_data.get("user_metadata", {})
        if user_metadata:
            user.full_name = user_metadata.get("full_name") or user_metadata.get("name")
            user.avatar_url = user_metadata.get("avatar_url")
            user.github_username = user_metadata.get("user_name") or user_metadata.get("preferred_username")
            user.github_avatar = user_metadata.get("avatar_url")
            user.auth_provider = "github"
        
        logger.info("User updated", user_id=user.id, email=email)
    else:
        # Create new user
        user_metadata = user_data.get("user_metadata", {})
        
        user = UserModel(
            supabase_id=supabase_id,
            email=email,
            email_confirmed=user_data.get("email_confirmed", False),
            full_name=user_metadata.get("full_name") or user_metadata.get("name"),
            avatar_url=user_metadata.get("avatar_url"),
            auth_provider="github",
            github_username=user_metadata.get("user_name") or user_metadata.get("preferred_username"),
            github_avatar=user_metadata.get("avatar_url"),
            is_active=True,
            is_verified=True  # GitHub users are auto-verified
        )
        
        session.add(user)
        await session.flush()  # Get the ID
        user.update_last_login()
        
        logger.info("User created", user_id=user.id, email=email)
    
    await session.commit()
    return user 