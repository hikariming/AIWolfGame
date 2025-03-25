"""
信任网络分析工具

功能：
1. 读取游戏数据JSON文件
2. 解析信任评分、投票数据和角色信息
3. 生成信任网络图
4. 分析信任关系和投票行为的相关性
5. 导出分析结果
"""

import json
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from datetime import datetime
import argparse
from typing import Dict, List, Any, Optional
import seaborn as sns

class TrustNetworkAnalyzer:
    def __init__(self, data_path: str):
        """初始化分析器
        
        Args:
            data_path: 数据文件路径或目录
        """
        self.data_path = data_path
        self.games_data = []
        self.trust_df = None
        self.votes_df = None
        self.players_df = None
        
        if os.path.isdir(data_path):
            # 读取目录下所有JSON文件
            for filename in os.listdir(data_path):
                if filename.endswith('.json'):
                    try:
                        file_path = os.path.join(data_path, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            game_data = json.load(f)
                            self.games_data.append(game_data)
                    except Exception as e:
                        print(f"读取文件 {filename} 时出错: {str(e)}")
        elif os.path.isfile(data_path) and data_path.endswith('.json'):
            # 读取单个JSON文件
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    game_data = json.load(f)
                    self.games_data.append(game_data)
            except Exception as e:
                print(f"读取文件 {data_path} 时出错: {str(e)}")
        else:
            raise ValueError(f"无效的数据路径: {data_path}")
        
        print(f"加载了 {len(self.games_data)} 个游戏数据")
        self._process_data()
    
    def _process_data(self):
        """处理游戏数据，转换为DataFrame"""
        trust_records = []
        vote_records = []
        player_records = []
        
        for game_idx, game_data in enumerate(self.games_data):
            game_id = game_data.get("game_id", f"game_{game_idx}")
            
            # 处理玩家角色信息
            player_roles = game_data.get("player_roles", {})
            for player_id, role_info in player_roles.items():
                player_records.append({
                    "game_id": game_id,
                    "player_id": player_id,
                    "player_name": role_info.get("name", ""),
                    "role_type": role_info.get("role_type", "")
                })
            
            # 处理信任评分数据
            rounds_data = game_data.get("rounds", [])
            for round_data in rounds_data:
                if "ratings" in round_data:
                    round_num = round_data.get("round", 0)
                    ratings = round_data.get("ratings", {})
                    
                    for rater_id, targets in ratings.items():
                        for target_id, rating in targets.items():
                            trust_records.append({
                                "game_id": game_id,
                                "round": round_num,
                                "rater_id": rater_id,
                                "rater_role": player_roles.get(rater_id, {}).get("role_type", ""),
                                "target_id": target_id,
                                "target_role": player_roles.get(target_id, {}).get("role_type", ""),
                                "trust_rating": rating,
                                "timestamp": round_data.get("timestamp", "")
                            })
                
                # 处理投票数据
                if "votes" in round_data:
                    round_num = round_data.get("round", 0)
                    votes = round_data.get("votes", [])
                    
                    for vote in votes:
                        vote_records.append({
                            "game_id": game_id,
                            "round": round_num,
                            "voter_id": vote.get("voter", ""),
                            "voter_role": vote.get("voter_role", ""),
                            "target_id": vote.get("target", ""),
                            "target_role": vote.get("target_role", ""),
                            "reason": vote.get("reason", ""),
                            "timestamp": vote.get("timestamp", "")
                        })
        
        # 创建DataFrame
        self.trust_df = pd.DataFrame(trust_records)
        self.votes_df = pd.DataFrame(vote_records)
        self.players_df = pd.DataFrame(player_records)
        
        print(f"处理了 {len(self.trust_df)} 条信任评分记录")
        print(f"处理了 {len(self.votes_df)} 条投票记录")
        print(f"处理了 {len(self.players_df)} 条玩家记录")
    
    def generate_trust_network(self, game_id: Optional[str] = None, round_num: Optional[int] = None, 
                               output_path: Optional[str] = None, show_plot: bool = True):
        """生成信任网络图
        
        Args:
            game_id: 游戏ID，如果为None则使用所有游戏
            round_num: 回合数，如果为None则使用所有回合
            output_path: 输出文件路径，如果为None则不保存
            show_plot: 是否显示图形
        """
        # 过滤数据
        df = self.trust_df
        
        if game_id:
            df = df[df["game_id"] == game_id]
            if df.empty:
                print(f"没有找到游戏ID为 {game_id} 的数据")
                return
        
        if round_num:
            df = df[df["round"] == round_num]
            if df.empty:
                print(f"没有找到回合数为 {round_num} 的数据")
                return
        
        # 创建有向图
        G = nx.DiGraph()
        
        # 添加节点和边
        for _, row in df.iterrows():
            G.add_node(row["rater_id"], role=row["rater_role"])
            G.add_node(row["target_id"], role=row["target_role"])
            
            # 检查是否已存在边，如果存在则计算平均值
            if G.has_edge(row["rater_id"], row["target_id"]):
                old_weight = G[row["rater_id"]][row["target_id"]]["weight"]
                old_count = G[row["rater_id"]][row["target_id"]].get("count", 1)
                new_weight = (old_weight * old_count + row["trust_rating"]) / (old_count + 1)
                G[row["rater_id"]][row["target_id"]]["weight"] = new_weight
                G[row["rater_id"]][row["target_id"]]["count"] = old_count + 1
            else:
                G.add_edge(row["rater_id"], row["target_id"], weight=row["trust_rating"], count=1)
        
        if len(G.nodes) == 0:
            print("没有足够的数据生成网络图")
            return
        
        # 设置节点颜色
        node_colors = []
        for node in G.nodes:
            role = G.nodes[node].get("role", "")
            if "werewolf" in role:
                node_colors.append("red")
            elif "villager" in role:
                node_colors.append("green")
            elif "seer" in role or "witch" in role or "hunter" in role:
                node_colors.append("blue")
            else:
                node_colors.append("gray")
        
        # 设置边的宽度和颜色
        edge_widths = []
        edge_colors = []
        for u, v, data in G.edges(data=True):
            weight = data.get("weight", 0)
            edge_widths.append(weight / 2)  # 根据权重设置边的宽度
            
            # 根据信任度设置颜色
            if weight >= 7:
                edge_colors.append("green")  # 高信任
            elif weight >= 4:
                edge_colors.append("blue")   # 中等信任
            else:
                edge_colors.append("red")    # 低信任
        
        # 创建图形
        plt.figure(figsize=(12, 12))
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # 绘制节点
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=500, alpha=0.8)
        
        # 绘制边
        nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color=edge_colors, 
                              arrowstyle='->', arrowsize=20, alpha=0.6)
        
        # 绘制标签
        nx.draw_networkx_labels(G, pos, font_size=12, font_family="sans-serif")
        
        # 添加边标签（信任分数）
        edge_labels = {(u, v): f"{d['weight']:.1f}" for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=10)
        
        # 设置标题
        title = "信任网络图"
        if game_id:
            title += f" - 游戏 {game_id}"
        if round_num:
            title += f" - 回合 {round_num}"
        plt.title(title)
        
        # 保存图形
        if output_path:
            plt.savefig(output_path, bbox_inches="tight")
            print(f"图形已保存到 {output_path}")
        
        # 显示图形
        if show_plot:
            plt.show()
        
        plt.close()
    
    def analyze_trust_vs_votes(self, game_id: Optional[str] = None, output_path: Optional[str] = None):
        """分析信任评分与投票行为的关系
        
        Args:
            game_id: 游戏ID，如果为None则使用所有游戏
            output_path: 输出文件路径，如果为None则不保存
        """
        # 过滤数据
        trust_df = self.trust_df
        votes_df = self.votes_df
        
        if game_id:
            trust_df = trust_df[trust_df["game_id"] == game_id]
            votes_df = votes_df[votes_df["game_id"] == game_id]
        
        if trust_df.empty or votes_df.empty:
            print("没有足够的数据进行分析")
            return
        
        # 合并投票数据与信任评分数据
        # 为每个投票找到对应的信任评分
        vote_trust_data = []
        
        for _, vote in votes_df.iterrows():
            # 查找该投票者对目标的信任评分
            matching_trust = trust_df[
                (trust_df["game_id"] == vote["game_id"]) &
                (trust_df["round"] == vote["round"]) &
                (trust_df["rater_id"] == vote["voter_id"]) &
                (trust_df["target_id"] == vote["target_id"])
            ]
            
            if not matching_trust.empty:
                trust_rating = matching_trust.iloc[0]["trust_rating"]
            else:
                # 如果找不到直接匹配，查找最近的一次信任评分
                prior_trust = trust_df[
                    (trust_df["game_id"] == vote["game_id"]) &
                    (trust_df["round"] <= vote["round"]) &
                    (trust_df["rater_id"] == vote["voter_id"]) &
                    (trust_df["target_id"] == vote["target_id"])
                ]
                
                if not prior_trust.empty:
                    # 选择最近的信任评分
                    trust_rating = prior_trust.sort_values("round", ascending=False).iloc[0]["trust_rating"]
                else:
                    trust_rating = None
            
            if trust_rating is not None:
                vote_trust_data.append({
                    "game_id": vote["game_id"],
                    "round": vote["round"],
                    "voter_id": vote["voter_id"],
                    "voter_role": vote["voter_role"],
                    "target_id": vote["target_id"],
                    "target_role": vote["target_role"],
                    "trust_rating": trust_rating
                })
        
        if not vote_trust_data:
            print("没有足够的匹配数据进行分析")
            return
        
        # 创建DataFrame
        vote_trust_df = pd.DataFrame(vote_trust_data)
        
        # 计算统计数据
        stats = {
            "voter_role": [],
            "target_role": [],
            "avg_trust": [],
            "count": []
        }
        
        for (v_role, t_role), group in vote_trust_df.groupby(["voter_role", "target_role"]):
            stats["voter_role"].append(v_role)
            stats["target_role"].append(t_role)
            stats["avg_trust"].append(group["trust_rating"].mean())
            stats["count"].append(len(group))
        
        stats_df = pd.DataFrame(stats)
        
        # 创建图形
        plt.figure(figsize=(10, 8))
        
        # 绘制热图
        pivot_df = stats_df.pivot(index="voter_role", columns="target_role", values="avg_trust")
        sns.heatmap(pivot_df, annot=True, cmap="YlGnBu", fmt=".1f", cbar_kws={"label": "平均信任评分"})
        
        # 设置标题和标签
        title = "投票者与目标之间的平均信任评分"
        if game_id:
            title += f" - 游戏 {game_id}"
        plt.title(title)
        plt.xlabel("目标角色")
        plt.ylabel("投票者角色")
        
        # 保存图形
        if output_path:
            plt.savefig(output_path, bbox_inches="tight")
            print(f"图形已保存到 {output_path}")
        
        plt.show()
        plt.close()
        
        # 输出统计信息
        print("投票与信任评分统计:")
        print(stats_df.sort_values(["voter_role", "target_role"]))
        
        # 分析同阵营和跨阵营的信任评分差异
        vote_trust_df["same_team"] = (
            ((vote_trust_df["voter_role"] == "werewolf") & (vote_trust_df["target_role"] == "werewolf")) |
            ((vote_trust_df["voter_role"] != "werewolf") & (vote_trust_df["target_role"] != "werewolf"))
        )
        
        team_stats = vote_trust_df.groupby("same_team")["trust_rating"].agg(["mean", "std", "count"])
        print("\n阵营内外信任评分差异:")
        print(team_stats)
        
        # 绘制箱线图
        plt.figure(figsize=(8, 6))
        sns.boxplot(x="same_team", y="trust_rating", data=vote_trust_df)
        plt.title("同阵营vs跨阵营信任评分分布")
        plt.xlabel("是否同阵营")
        plt.ylabel("信任评分")
        plt.xticks([0, 1], ["不同阵营", "同阵营"])
        
        if output_path:
            base_name = os.path.splitext(output_path)[0]
            plt.savefig(f"{base_name}_boxplot.png", bbox_inches="tight")
        
        plt.show()
        plt.close()
    
    def export_data(self, output_dir: str):
        """导出处理后的数据到CSV文件
        
        Args:
            output_dir: 输出目录
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 导出信任评分数据
        if self.trust_df is not None and not self.trust_df.empty:
            trust_path = os.path.join(output_dir, "trust_ratings.csv")
            self.trust_df.to_csv(trust_path, index=False)
            print(f"信任评分数据已导出到 {trust_path}")
        
        # 导出投票数据
        if self.votes_df is not None and not self.votes_df.empty:
            votes_path = os.path.join(output_dir, "votes.csv")
            self.votes_df.to_csv(votes_path, index=False)
            print(f"投票数据已导出到 {votes_path}")
        
        # 导出玩家数据
        if self.players_df is not None and not self.players_df.empty:
            players_path = os.path.join(output_dir, "players.csv")
            self.players_df.to_csv(players_path, index=False)
            print(f"玩家数据已导出到 {players_path}")


def main():
    parser = argparse.ArgumentParser(description="狼人杀信任网络分析工具")
    parser.add_argument("data_path", help="游戏数据文件路径或目录")
    parser.add_argument("--game", help="指定要分析的游戏ID")
    parser.add_argument("--round", type=int, help="指定要分析的回合数")
    parser.add_argument("--output", help="输出文件/目录路径")
    parser.add_argument("--export", action="store_true", help="是否导出处理后的数据")
    parser.add_argument("--analyze-votes", action="store_true", help="分析投票与信任评分的关系")
    
    args = parser.parse_args()
    
    try:
        analyzer = TrustNetworkAnalyzer(args.data_path)
        
        # 生成信任网络图
        output_path = None
        if args.output:
            if args.output.endswith(".png"):
                output_path = args.output
            else:
                if not os.path.exists(args.output):
                    os.makedirs(args.output)
                output_path = os.path.join(args.output, f"trust_network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        analyzer.generate_trust_network(args.game, args.round, output_path)
        
        # 分析投票与信任评分的关系
        if args.analyze_votes:
            vote_output = None
            if args.output:
                if os.path.isdir(args.output):
                    vote_output = os.path.join(args.output, f"trust_vs_votes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                else:
                    vote_output = os.path.splitext(args.output)[0] + "_votes.png"
            
            analyzer.analyze_trust_vs_votes(args.game, vote_output)
        
        # 导出数据
        if args.export:
            export_dir = args.output if args.output and os.path.isdir(args.output) else "exported_data"
            analyzer.export_data(export_dir)
        
    except Exception as e:
        print(f"分析过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 