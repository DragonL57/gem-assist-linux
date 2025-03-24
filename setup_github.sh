#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Git repository for gem-assist-linux...${NC}"

# Initialize Git repository if not already done
if [ ! -d .git ]; then
    echo -e "${BLUE}Initializing Git repository...${NC}"
    git init
    echo -e "${GREEN}Git repository initialized.${NC}"
else
    echo -e "${YELLOW}Git repository already exists.${NC}"
fi

# Add all files
echo -e "${BLUE}Adding files to Git...${NC}"
git add .

# Commit changes
echo -e "${BLUE}Committing changes...${NC}"
git commit -m "updated reame.md"

# Check if the remote exists
REMOTE_EXISTS=$(git remote | grep origin)
if [ -z "$REMOTE_EXISTS" ]; then
    echo -e "${BLUE}Adding remote repository...${NC}"
    git remote add origin https://github.com/DragonL57/gem-assist-linux.git
else
    echo -e "${YELLOW}Remote 'origin' already exists.${NC}"
fi

# Set the main branch
echo -e "${BLUE}Setting up main branch...${NC}"
git branch -M main

# Push to GitHub
echo -e "${BLUE}Pushing to GitHub...${NC}"
git push -u origin main

echo -e "${GREEN}Setup complete! Your project has been pushed to GitHub.${NC}"
