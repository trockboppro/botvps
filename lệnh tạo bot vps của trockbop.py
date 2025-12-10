import discord
from discord import app_commands
import asyncio
import subprocess
import psutil
import time

TOKEN = "MTM2NzM3NDM4NjE1OTQxOTQ5Mw.GUrzuI.D4ZVyvPswEbLrFDeYeTP-7iho2d0k4ComTjXho"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

count_create = 0  # Đếm số VPS đã tạo

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def list_vps_containers():
    out = run_cmd("docker ps -a --filter 'name=vps_' --format '{{.ID}} | {{.Names}} | {{.Status}}'")
    return out if out else "Chưa có VPS nào."

async def update_activity():
    global count_create
    game = discord.Game(name=f"Đã tạo {count_create} VPS")
    await client.change_presence(status=discord.Status.online, activity=game)

@tree.command(name="node", description="Xem trạng thái bot và RAM máy chủ")
async def node(interaction: discord.Interaction):
    ram = psutil.virtual_memory()
    embed = discord.Embed(title="📊 Trạng thái Bot", color=0x00ff00)
    embed.add_field(name="Trạng thái", value="Online", inline=True)
    embed.add_field(name="RAM tổng", value=f"{ram.total // 1024 // 1024} MB", inline=True)
    embed.add_field(name="RAM sử dụng", value=f"{ram.used // 1024 // 1024} MB", inline=True)
    await interaction.response.send_message(embed=embed)

@tree.command(name="list", description="Hiển thị danh sách VPS")
async def list_vps(interaction: discord.Interaction):
    data = list_vps_containers()
    embed = discord.Embed(title="📋 Danh sách VPS", description=data, color=0x3498db)
    await interaction.response.send_message(embed=embed)

@tree.command(name="create", description="Tạo VPS Ubuntu mới")
async def create_vps(interaction: discord.Interaction):
    global count_create
    await interaction.response.defer()
    name = f"vps_{int(time.time())}"
    cmd = f"docker run -dit --name {name} ubuntu:22.04 /bin/bash"
    result = run_cmd(cmd)
    if "Error" in result:
        await interaction.followup.send(f"❌ Tạo VPS thất bại: {result}")
        return
    # Cài tmate và openssh-client trong VPS mới
    run_cmd(f"docker exec {name} bash -c 'apt update && apt install -y tmate openssh-client'")
    count_create += 1
    await update_activity()
    embed = discord.Embed(title="✅ VPS mới đã tạo", color=0x00ff00)
    embed.add_field(name="ID VPS", value=name, inline=False)
    embed.add_field(name="Trạng thái", value="Đang chạy", inline=True)
    embed.add_field(name="Hướng dẫn", value=f"Sử dụng lệnh `/ssh {name}` để kết nối qua tmate", inline=False)
    embed.set_footer(text=f"Tổng số VPS đã tạo: {count_create}")
    await interaction.followup.send(embed=embed)

@tree.command(name="stop", description="Dừng VPS theo id")
@app_commands.describe(vps_id="ID hoặc tên VPS")
async def stop_vps(interaction: discord.Interaction, vps_id: str):
    out = run_cmd(f"docker stop {vps_id}")
    embed = discord.Embed(title=f"⏹ VPS {vps_id} đã dừng", description=out, color=0xffa500)
    await interaction.response.send_message(embed=embed)

@tree.command(name="start", description="Khởi động VPS theo id")
@app_commands.describe(vps_id="ID hoặc tên VPS")
async def start_vps(interaction: discord.Interaction, vps_id: str):
    out = run_cmd(f"docker start {vps_id}")
    embed = discord.Embed(title=f"▶ VPS {vps_id} đã khởi động", description=out, color=0x00ff00)
    await interaction.response.send_message(embed=embed)

@tree.command(name="restart", description="Khởi động lại VPS theo id")
@app_commands.describe(vps_id="ID hoặc tên VPS")
async def restart_vps(interaction: discord.Interaction, vps_id: str):
    out = run_cmd(f"docker restart {vps_id}")
    embed = discord.Embed(title=f"🔄 VPS {vps_id} đã khởi động lại", description=out, color=0x3498db)
    await interaction.response.send_message(embed=embed)

@tree.command(name="show-vps", description="Hiển thị trạng thái VPS")
@app_commands.describe(vps_id="ID hoặc tên VPS")
async def show_vps(interaction: discord.Interaction, vps_id: str):
    status = run_cmd(f"docker inspect -f '{{{{.State.Status}}}}' {vps_id}")
    if "Error" in status:
        await interaction.response.send_message(f"❌ VPS {vps_id} không tồn tại.")
        return
    stats = run_cmd(f"docker stats {vps_id} --no-stream --format 'CPU: {{.CPUPerc}}, RAM: {{.MemUsage}}'")
    embed = discord.Embed(title=f"ℹ Thông tin VPS {vps_id}", color=0x3498db)
    embed.add_field(name="Trạng thái", value=status, inline=True)
    embed.add_field(name="CPU và RAM", value=stats, inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="ssh", description="Tạo phiên SSH qua tmate vào VPS theo id")
@app_commands.describe(vps_id="ID hoặc tên VPS")
async def ssh_vps(interaction: discord.Interaction, vps_id: str):
    await interaction.response.defer()
    status = run_cmd(f"docker inspect -f '{{{{.State.Status}}}}' {vps_id}")
    if "running" not in status:
        await interaction.followup.send(f"❌ VPS {vps_id} không tồn tại hoặc không đang chạy.")
        return
    # Khởi chạy tmate session trong container
    run_cmd(f"docker exec -d {vps_id} tmate -S /tmp/tmate.sock new-session -d")
    await asyncio.sleep(2)  # đợi tmate khởi động
    ssh_url = run_cmd(f"docker exec {vps_id} tmate -S /tmp/tmate.sock display -p '#{{tmate_ssh}}'")
    if ssh_url and "Error" not in ssh_url and ssh_url.strip() != "":
        embed = discord.Embed(title=f"🔗 SSH tmate VPS {vps_id}", description=f"```{ssh_url}```", color=0x00ff00)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Không tạo được phiên SSH tmate cho VPS {vps_id}.")

@tree.command(name="open-port", description="Mở port qua serveo.net")
@app_commands.describe(vps_id="ID VPS", port="Port cần mở")
async def open_port(interaction: discord.Interaction, vps_id: str, port: int):
    msg = (f"Mở port `{port}` cho VPS `{vps_id}` qua serveo.net.\n"
           f"Vui lòng chạy lệnh sau trên server VPS để mở port:\n"
           f"```ssh -R 80:localhost:{port} serveo.net```")
    embed = discord.Embed(title="🌐 Mở Port qua Serveo", description=msg, color=0x3498db)
    await interaction.response.send_message(embed=embed)

@client.event
async def on_ready():
    print(f"Bot đã đăng nhập: {client.user}")
    global count_create
    await update_activity()
    await tree.sync()

client.run(TOKEN)
