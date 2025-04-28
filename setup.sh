#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Jira MCP setup...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}pip3 is not installed. Please install pip3 and try again.${NC}"
    exit 1
fi

# Create virtual environment
echo -e "${YELLOW}Creating virtual environment...${NC}"
python3 -m venv venv

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << EOL
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-api-token
EOL
    echo -e "${GREEN}.env file created. Please update it with your Jira credentials.${NC}"
fi

# Make the script executable
chmod +x main.py

echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Update the .env file with your Jira credentials"
echo "2. Run the MCP server:"
echo "   - For stdio transport: ./main.py"
echo "   - For SSE transport: ./main.py --transport sse --port 8000"

# Add helpful aliases to .bashrc or .zshrc
if [ -f ~/.bashrc ]; then
    if ! grep -q "alias jira-mcp=" ~/.bashrc; then
        echo "alias jira-mcp='source venv/bin/activate && ./main.py'" >> ~/.bashrc
        echo -e "${GREEN}Added jira-mcp alias to .bashrc${NC}"
    fi
fi

if [ -f ~/.zshrc ]; then
    if ! grep -q "alias jira-mcp=" ~/.zshrc; then
        echo "alias jira-mcp='source venv/bin/activate && ./main.py'" >> ~/.zshrc
        echo -e "${GREEN}Added jira-mcp alias to .zshrc${NC}"
    fi
fi

echo -e "${GREEN}To start using the MCP, run:${NC}"
echo -e "${YELLOW}source venv/bin/activate${NC}"
echo -e "${YELLOW}./main.py${NC}" 