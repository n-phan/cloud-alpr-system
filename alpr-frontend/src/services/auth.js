import { Amplify } from 'aws-amplify';
import { signUp, signIn, signOut, getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';

// Configure Amplify
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      region: import.meta.env.VITE_COGNITO_REGION,
    }
  }
});

/**
 * Sign up a new user
 */
export const handleSignUp = async (email, password) => {
  try {
    const { userId } = await signUp({
      username: email,
      password,
      options: {
        userAttributes: {
          email,
        }
      }
    });
    console.log('Sign up successful:', userId);
    return { userId };
  } catch (error) {
    console.error('Sign up error:', error);
    throw error;
  }
};

/**
 * Sign in a user
 */
export const handleSignIn = async (email, password) => {
  try {
    const { isSignedIn, nextStep } = await signIn({
      username: email,
      password,
    });

    if (nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
      throw new Error('Please confirm your new password');
    }

    console.log('Sign in successful');
    return { isSignedIn };
  } catch (error) {
    console.error('Sign in error:', error);
    throw error;
  }
};

/**
 * Sign out the current user
 */
export const handleSignOut = async () => {
  try {
    await signOut();
    console.log('Sign out successful');
  } catch (error) {
    console.error('Sign out error:', error);
    throw error;
  }
};

/**
 * Get currently authenticated user
 */
export const getAuthenticatedUser = async () => {
  try {
    const user = await getCurrentUser();
    console.log('Authenticated user:', user);
    return {
      userId: user.userId,
      email: user.signInDetails?.loginId || user.username,
      username: user.username
    };
  } catch (error) {
    console.error('Get user error:', error);
    return null;
  }
};

/**
 * Check if user is authenticated
 */
export const isUserAuthenticated = async () => {
  try {
    const user = await getCurrentUser();
    return !!user;
  } catch (error) {
    return false;
  }
};

/**
 * Check if user is in admin group
 */
export const isUserAdmin = async () => {
  try {
    const session = await fetchAuthSession();
    const idToken = session?.tokens?.idToken;
    
    if (!idToken) {
      console.log('No ID token found');
      return false;
    }

    // Get the payload from the token
    const payload = idToken.payload;
    const groups = payload?.['cognito:groups'] || [];
    
    console.log('User groups:', groups);
    const isAdmin = groups.includes('admin');
    console.log('Is admin:', isAdmin);
    
    return isAdmin;
  } catch (error) {
    console.error('Error checking admin status:', error);
    return false;
  }
};
