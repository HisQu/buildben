import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { App } from './App';

describe('App', () => {
  it('increments the displayed count when activated', async () => {
    const user = userEvent.setup();
    render(<App projectName="Example" />);

    expect(screen.getByRole('heading', { name: 'Example' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Count: 0');

    await user.click(screen.getByRole('button', { name: 'Increment' }));

    expect(screen.getByRole('status')).toHaveTextContent('Count: 1');
  });
});
