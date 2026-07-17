import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import PrivateRoute from '../components/Auth/PrivateRoute';

// Use a mutable mock function that can change return value per test
const mockUseAuth = vi.fn();
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('PrivateRoute', () => {
  it('renders children when role matches', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'customer' }, loading: false });
    render(
      <MemoryRouter>
        <PrivateRoute roleRequired="customer">
          <div>Protected Content</div>
        </PrivateRoute>
      </MemoryRouter>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('redirects to login when no user', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false });
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <PrivateRoute roleRequired="customer">
          <div>Protected Content</div>
        </PrivateRoute>
      </MemoryRouter>
    );

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('redirects when role does not match', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'customer' }, loading: false });
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <PrivateRoute roleRequired="admin">
          <div>Admin Content</div>
        </PrivateRoute>
      </MemoryRouter>
    );

    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
  });
});
