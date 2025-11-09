#!/usr/bin/env python3
"""
Admin CLI tool for managing AX5 plotter users.
"""
import sys
import os
import click
from getpass import getpass
from tabulate import tabulate

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.api.auth import SessionLocal, User, create_user, pwd_context


@click.group()
def cli():
    """AX5 Plotter Admin CLI"""
    pass


@cli.command()
@click.option('--username', prompt=True)
@click.option('--email', prompt=True)
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@click.option('--admin', is_flag=True, help='Create as admin user')
def create(username, email, password, admin):
    """Create new user"""
    db = SessionLocal()
    try:
        user = create_user(username, email, password, is_admin=admin, db=db)
        click.echo(f"\n✓ User created successfully!")
        click.echo(f"  Username: {user.username}")
        click.echo(f"  Email: {user.email}")
        click.echo(f"  API Key: {user.api_key}")
        click.echo(f"  Admin: {user.is_admin}")
    except ValueError as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)
    finally:
        db.close()


@cli.command()
def list():
    """List all users"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        
        if not users:
            click.echo("No users found")
            return
        
        table_data = []
        for user in users:
            table_data.append([
                user.id,
                user.username,
                user.email,
                "✓" if user.is_active else "✗",
                "✓" if user.is_admin else "",
                user.total_jobs,
                f"{user.total_plot_time/60:.1f}m",
                user.created_at.strftime("%Y-%m-%d")
            ])
        
        headers = ["ID", "Username", "Email", "Active", "Admin", "Jobs", "Time", "Created"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
        
    finally:
        db.close()


@cli.command()
@click.argument('username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
def reset_password(username, password):
    """Reset user password"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            click.echo(f"✗ User '{username}' not found", err=True)
            sys.exit(1)
        
        user.set_password(password)
        db.commit()
        
        click.echo(f"✓ Password reset for user: {username}")
        
    finally:
        db.close()


@cli.command()
@click.argument('username')
def reset_api_key(username):
    """Generate new API key for user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            click.echo(f"✗ User '{username}' not found", err=True)
            sys.exit(1)
        
        new_key = user.generate_api_key()
        db.commit()
        
        click.echo(f"✓ New API key for {username}:")
        click.echo(f"  {new_key}")
        
    finally:
        db.close()


@cli.command()
@click.argument('username')
@click.option('--jobs-per-hour', type=int)
@click.option('--jobs-per-day', type=int)
@click.option('--max-duration', type=int)
def set_limits(username, jobs_per_hour, jobs_per_day, max_duration):
    """Set rate limits for user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            click.echo(f"✗ User '{username}' not found", err=True)
            sys.exit(1)
        
        if jobs_per_hour is not None:
            user.jobs_per_hour = jobs_per_hour
        if jobs_per_day is not None:
            user.jobs_per_day = jobs_per_day
        if max_duration is not None:
            user.max_job_duration = max_duration
        
        db.commit()
        
        click.echo(f"✓ Limits updated for {username}:")
        click.echo(f"  Jobs per hour: {user.jobs_per_hour}")
        click.echo(f"  Jobs per day: {user.jobs_per_day}")
        click.echo(f"  Max duration: {user.max_job_duration}s")
        
    finally:
        db.close()


@cli.command()
@click.argument('username')
@click.option('--active/--inactive', default=None)
@click.option('--admin/--no-admin', default=None)
def modify(username, active, admin):
    """Modify user permissions"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            click.echo(f"✗ User '{username}' not found", err=True)
            sys.exit(1)
        
        if active is not None:
            user.is_active = active
        if admin is not None:
            user.is_admin = admin
        
        db.commit()
        
        click.echo(f"✓ User {username} updated:")
        click.echo(f"  Active: {user.is_active}")
        click.echo(f"  Admin: {user.is_admin}")
        
    finally:
        db.close()


@cli.command()
@click.argument('username')
@click.confirmation_option(prompt='Are you sure you want to delete this user?')
def delete(username):
    """Delete user (cannot be undone)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            click.echo(f"✗ User '{username}' not found", err=True)
            sys.exit(1)
        
        if user.is_admin:
            admin_count = db.query(User).filter(User.is_admin == True).count()
            if admin_count <= 1:
                click.echo("✗ Cannot delete the last admin user", err=True)
                sys.exit(1)
        
        db.delete(user)
        db.commit()
        
        click.echo(f"✓ User {username} deleted")
        
    finally:
        db.close()


@cli.command()
@click.argument('username')
def info(username):
    """Show detailed user information"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            click.echo(f"✗ User '{username}' not found", err=True)
            sys.exit(1)
        
        click.echo(f"\nUser Information:")
        click.echo(f"  ID: {user.id}")
        click.echo(f"  Username: {user.username}")
        click.echo(f"  Email: {user.email}")
        click.echo(f"  Active: {user.is_active}")
        click.echo(f"  Admin: {user.is_admin}")
        click.echo(f"\nAPI Key:")
        click.echo(f"  {user.api_key}")
        click.echo(f"\nRate Limits:")
        click.echo(f"  Jobs per hour: {user.jobs_per_hour}")
        click.echo(f"  Jobs per day: {user.jobs_per_day}")
        click.echo(f"  Max job duration: {user.max_job_duration}s")
        click.echo(f"\nUsage Statistics:")
        click.echo(f"  Total jobs: {user.total_jobs}")
        click.echo(f"  Total plot time: {user.total_plot_time/3600:.2f} hours")
        click.echo(f"\nTimestamps:")
        click.echo(f"  Created: {user.created_at}")
        click.echo(f"  Last login: {user.last_login or 'Never'}")
        
    finally:
        db.close()


if __name__ == '__main__':
    cli()
