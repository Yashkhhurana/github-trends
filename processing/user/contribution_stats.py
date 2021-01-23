from collections import defaultdict
from typing import Callable, Dict, DefaultDict, List, Optional

from external.github_api.graphql.user import (
    get_user_contribution_stats as run_query,
)
from models.misc.date import Date, today

from models.user.contribution_stats import (
    APIResponse_ContribsByRepo,
    Contribution,
    RepoContribStats,
    ContribStats,
)


def get_user_contribution_stats(
    user_id: str,
    max_repos: int = 100,
    start_date: Date = today - 365,
    end_date: Date = today,
) -> ContribStats:
    """Gets the daily contribution history for a users top x repositories"""
    repo_names = set()
    repo_contribs: DefaultDict[str, Dict[str, List[Contribution]]] = defaultdict(
        lambda: {"issues": [], "prs": [], "reviews": [], "repo": []}
    )
    total_contribs: Dict[str, List[Contribution]] = {
        "issues": [],
        "prs": [],
        "reviews": [],
        "repo": [],
    }

    # only need them from the first data pull
    restricted_contrib_count = 0
    issue_contribs_count = 0
    pr_contribs_count = 0
    pr_review_contribs_count = 0
    repo_contribs_count = 0
    repos_with_issue_contrib = 0
    repos_with_pr_contrib = 0
    repos_with_pr_review_contrib = 0

    after: Optional[str] = ""
    index, cont = 0, True  # initialize variables
    while cont and index < 10:
        try:
            after_str: str = after if isinstance(after, str) else ""
            data = run_query(user_id, max_repos, after=after_str)
        except Exception as e:
            raise e

        restricted_contrib_count = data.restricted_contrib_count
        issue_contribs_count = data.issue_contribs_count
        pr_contribs_count = data.pr_contribs_count
        pr_review_contribs_count = data.pr_review_contribs_count
        repo_contribs_count = data.repo_contribs_count
        repos_with_issue_contrib = data.repos_with_issue_contrib
        repos_with_pr_contrib = data.repos_with_pr_contrib
        repos_with_pr_review_contrib = data.repos_with_pr_review_contrib

        for repo in data.issue_contribs_by_repo:
            repo_names.add(repo.repository.name)
        for repo in data.pr_contribs_by_repo:
            repo_names.add(repo.repository.name)
        for repo in data.pr_review_contribs_by_repo:
            repo_names.add(repo.repository.name)
        for repo in data.repo_contribs.nodes:
            repo_names.add(repo.repository.name)

        cont = False
        repo_lists: List[List[APIResponse_ContribsByRepo]] = [
            data.issue_contribs_by_repo,
            data.pr_contribs_by_repo,
            data.pr_review_contribs_by_repo,
        ]
        for category, repo_list in zip(["issues", "prs", "reviews"], repo_lists):
            for repo in repo_list:
                repo_name = repo.repository.name
                for event in repo.contributions.nodes:
                    contrib = Contribution(occurred_at=Date(event.occurred_at))
                    repo_contribs[repo_name][category].append(contrib)
                    total_contribs[category].append(contrib)
                if repo.contributions.page_info.has_next_page:
                    after = repo.contributions.page_info.end_cursor
                    cont = True

        for repo in data.repo_contribs.nodes:
            contrib = Contribution(occurred_at=Date(repo.occurred_at))
            repo_contribs[repo.repository.name]["repo"].append(contrib)
            total_contribs["repo"].append(contrib)

        index += 1

    date_filter: Callable[[Contribution], bool] = (
        lambda x: start_date <= x.occurred_at <= end_date
    )

    repo_contrib_objs: List[RepoContribStats] = [
        RepoContribStats(
            name=k,
            issues=list(filter(date_filter, v["issues"])),
            prs=list(filter(date_filter, v["prs"])),
            reviews=list(filter(date_filter, v["reviews"])),
            repo=list(filter(date_filter, v["repo"])),
        )
        for k, v in repo_contribs.items()
    ]

    # can get more than max_repos outputs if issues/prs/reviews come from different repos
    repo_contrib_objs = sorted(
        repo_contrib_objs,
        key=lambda x: len(x.issues) + len(x.prs) + len(x.reviews) + len(x.repo),
        reverse=True,
    )[:max_repos]

    total_contrib_obj: RepoContribStats = RepoContribStats(
        name="total",
        issues=list(filter(date_filter, total_contribs["issues"])),
        prs=list(filter(date_filter, total_contribs["prs"])),
        reviews=list(filter(date_filter, total_contribs["reviews"])),
        repo=list(filter(date_filter, total_contribs["repo"])),
    )

    output: ContribStats = ContribStats(
        total=total_contrib_obj,
        repos=repo_contrib_objs,
        restricted_contrib_count=restricted_contrib_count,
        issue_contribs_count=issue_contribs_count,
        pr_contribs_count=pr_contribs_count,
        pr_review_contribs_count=pr_review_contribs_count,
        repo_contribs_count=repo_contribs_count,
        repos_with_issue_contrib=repos_with_issue_contrib,
        repos_with_pr_contrib=repos_with_pr_contrib,
        repos_with_pr_review_contrib=repos_with_pr_review_contrib,
    )

    return output