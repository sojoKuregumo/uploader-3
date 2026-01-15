# Use Ubuntu 22.04 as the base (matches the MEGA version you were using)
FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install Python and system tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wget \
    libc-bin \
    && rm -rf /var/lib/apt/lists/*

# 2. Download and Install MEGA-CMD properly
RUN wget -q https://mega.nz/linux/repo/xUbuntu_22.04/amd64/megacmd-xUbuntu_22.04_amd64.deb \
    && apt-get update \
    && apt-get install -y ./megacmd-xUbuntu_22.04_amd64.deb \
    && rm megacmd-xUbuntu_22.04_amd64.deb

# 3. COMPATIBILITY TRICK: 
# Your main.py looks for mega in "mega_local/usr/bin/mega-cmd".
# We create a "symlink" so your code finds it there without you needing to edit main.py.
WORKDIR /app
RUN mkdir -p mega_local/usr/bin/ \
    && ln -s /usr/bin/mega-cmd /app/mega_local/usr/bin/mega-cmd

# 4. Install Python Requirements
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# 5. Copy the rest of your code
COPY . .

# 6. Run the bot
CMD ["python3", "main.py"]
