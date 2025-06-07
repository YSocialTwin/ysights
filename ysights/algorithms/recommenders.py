from ysights import YDataHandler
from collections import defaultdict
import math


def engagement_momentum(YDH: YDataHandler, time_window_rounds: int = 24):
    """
    Calculate the engagement momentum for each post based on the number of recommendations over time.
    This function aggregates the number of recommendations for each post across time slots defined by the
    specified time window in rounds. The momentum is calculated using an exponential decay function
    to give more weight to recent recommendations.
    The momentum for each post is defined as the sum of the number of recommendations in each time slot,
    weighted by an exponential decay factor based on the slot index.
    The formula used is:
        momentum(post_id) = sum(exp(-0.1 * slot) * count)
    where `slot` is the time slot index and `count` is the number of recommendations in that slot.

    :param YDH: YDataHandler instance for database operations
    :param time_window_rounds: the number of rounds to consider for each time slot
    :return: a dictionary with post IDs as keys and their engagement momentum as values
    """

    # get all recommendations
    query = """
        SELECT r.post_ids, r.round
        FROM recommendations AS r
        ORDER BY r.round ASC
    """
    rows = YDH.custom_query(query)

    post_to_slot_to_count = defaultdict(lambda: defaultdict(int))
    for row in rows:
        post_ids = row[0].split("|")
        slot = row[1] // time_window_rounds
        for post_id in post_ids:
            post_to_slot_to_count[post_id][slot] += 1

    # calculate the momentum for each post
    momentum = defaultdict(float)
    for post_id, slots in post_to_slot_to_count.items():
        mom = 0
        for slot, count in slots.items():
            mom += math.exp(-0.1 * slot) * count

        momentum[post_id] = mom

    return momentum


def personalization_balance_score(
    YDH: YDataHandler, time_window_rounds: int = 24, alpha=0.5
):
    """
    Calculate the personalization balance score for each user based on their posts and interests.
    The balance score is a combination of the match rate and niche rate, where the match rate
    is the ratio of posts that match the user's interests to the total number of posts,
    and the niche rate is the ratio of popular posts in the user's interest slots to the total number of posts.
    The function retrieves user posts and interests from the database, calculates the match and niche rates,
    and combines them using the specified alpha parameter to produce a balance score for each user.
    The balance score is defined as:
        balance_score(user) = alpha * match_rate(user) + (1 - alpha) * niche_rate(user)

    This function is useful for evaluating how well the content of posts aligns with the interests of the users,
    providing a measure of content personalization and relevance.

    :param YDH: YDataHandler instance for database operations
    :param time_window_rounds: the number of rounds to consider for each time slot
    :param alpha: the weight for the match rate in the balance score calculation
    :return: a dictionary with user IDs as keys and their personalization balance scores as values
    """
    # get all recommendations
    query = """
            SELECT r.post_ids, r.round, r.user_id
            FROM recommendations AS r
            ORDER BY r.round ASC \
            """
    rows = YDH.custom_query(query)

    user_to_slot_to_posts = defaultdict(lambda: defaultdict(list))
    for row in rows:
        post_ids = row[0].split("|")
        slot = row[1] // time_window_rounds
        user_id = row[2]
        for post_id in post_ids:
            user_to_slot_to_posts[user_id][slot].append(post_id)

    query = """
            SELECT r.post_id, r.topic_id
            FROM post_topics AS r
            """
    rows = YDH.custom_query(query)
    post_topics = defaultdict(list)
    for row in rows:
        post_id = row[0]
        topic_id = row[1]
        post_topics[post_id].append(topic_id)

    query = """
            SELECT r.user_id, r.interest_id, r.round_id
            FROM user_interest AS r 
            ORDER BY r.round_id ASC
            """
    rows = YDH.custom_query(query)

    user_to_slot_to_interest = defaultdict(lambda: defaultdict(list))
    for row in rows:
        user_id = row[0]
        interest_id = row[1]
        slot = row[2] // time_window_rounds
        user_to_slot_to_interest[user_id][slot].append(interest_id)

    def match_rate(user_to_slot_to_posts, post_topics, user_to_slot_to_interest):
        """
        Calculate the match rate for each user based on their posts and interests.
        The match rate is defined as the ratio of the number of posts that match the user's interests
        to the total number of posts made by the user in the given time slots.
        The function iterates through each user and their posts, checking if the topics of the posts
        match the user's interests. The score is calculated as the number of matching topics divided
        by the total number of posts made by the user in the time slots.
        This function is useful for evaluating how well the content of posts aligns with the interests
        of the users, providing a measure of content personalization and relevance.

        :param user_to_slot_to_posts:
        :param post_topics:
        :param user_to_slot_to_interest:
        :return:
        """

        m_rate = defaultdict(float)

        user_to_posts = {
            user: set(post for posts in time_to_posts.values() for post in posts)
            for user, time_to_posts in user_to_slot_to_posts.items()
        }

        for user_in in user_to_slot_to_posts:
            score = 0
            for slot, posts in user_to_slot_to_interest[user_in].items():
                for post in posts:
                    if post in post_topics:
                        topics = post_topics[post]
                        for topic in topics:
                            if topic in user_to_slot_to_interest[user_in][slot]:
                                score += 1
            score = score / len(user_to_posts[user_in])
            m_rate[user_in] = score

        return m_rate

    def niche_rate(
        user_to_slot_to_posts, post_topics, user_to_slot_to_interest, tau=0.25
    ):
        """
        Calculate the niche rate for each user based on their posts and interests.
        The niche rate is defined as the ratio of the number of posts that are popular in the user's
        interest slots to the total number of posts made by the user in the given time slots.
        The function iterates through each user and their posts, checking if the topics of the posts
        match the user's interests and if the popularity of the posts exceeds a given threshold (tau).
        The score is calculated as the number of popular posts divided by the total number of posts
        made by the user in the time slots.
        This function is useful for evaluating how well the content of posts aligns with the interests
        of the users, providing a measure of content personalization and relevance, particularly focusing
        on niche content that is popular among users.

        :param user_to_slot_to_posts:
        :param post_topics:
        :param user_to_slot_to_interest:
        :param tau:
        :return:
        """

        n_rate = defaultdict(float)

        user_to_posts = {
            user: set(post for posts in time_to_posts.values() for post in posts)
            for user, time_to_posts in user_to_slot_to_posts.items()
        }

        # extract post popularity per slot normalized in [0,1]
        post_popularity = defaultdict(lambda: defaultdict(int))
        for user, time_to_posts in user_to_slot_to_posts.items():
            for slot, posts in time_to_posts.items():
                for post in posts:
                    post_popularity[slot][post] += 1

        # normalize the popularity
        for slot, posts in post_popularity.items():
            max_popularity = max(posts.values())
            for post in posts:
                post_popularity[slot][post] /= max_popularity

        for user_in in user_to_slot_to_posts:
            score = 0
            for slot, posts in user_to_slot_to_interest[user_in].items():
                for post in posts:
                    if post in post_topics:
                        topics = post_topics[post]
                        for topic in topics:
                            if topic in user_to_slot_to_interest[user_in][slot]:
                                # calculate the popularity of the post
                                popularity = post_popularity[slot][post]
                                if popularity > tau:
                                    score += 1
            score = score / len(user_to_posts[user_in])
            n_rate[user_in] = score

        return n_rate

    match = match_rate(user_to_slot_to_posts, post_topics, user_to_slot_to_interest)
    niche = niche_rate(user_to_slot_to_posts, post_topics, user_to_slot_to_interest)
    balance_score = defaultdict(float)

    for user in match:
        if user in niche:
            balance_score[user] = alpha * match[user] + (1 - alpha) * niche[user]
        else:
            balance_score[user] = match[user]
    return balance_score


def sentiment_diffusion_metrics(YDH: YDataHandler):
    pass
