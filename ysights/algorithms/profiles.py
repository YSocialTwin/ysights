from collections import defaultdict
from ysights.models.YDataHandler import YDataHandler


def profile_topics_similarity(
    YDH: YDataHandler, g, limit=2, from_round=None, to_round=None
):
    """
    Compute the similarity between each user and its neighbors based on their interests.

    :param YDH: YDataHandler instance for database operations
    :param g: networkx graph representing the social network
    :param limit: the minimum count of interests to consider
    :param from_round: the starting round for filtering interests
    :param to_round: the ending round for filtering interests
    :return: a dictionary with user IDs as keys and their similarity scores as values
    """
    # get the count of each interest per user
    query = "SELECT u.user_id, i.interest FROM user_interest as u, interests as i WHERE u.interest_id = i.iid"
    if from_round is not None:
        query += f" and u.round_id >= {from_round}"
    if to_round is not None:
        query += f" and u.round_id <= {to_round}"

    data = YDH.custom_query(query)

    interest_count = defaultdict(lambda: defaultdict(float))
    for row in data:
        user_id = row[0]
        interest = (
            row[1].strip().lower()
        )  # Assuming interests are stored as a comma-separated string
        interest_count[user_id][interest] += 1

        # remove rare interests from the interest_count
    for user_id, interests in interest_count.items():
        for interest, count in list(interests.items()):
            if count < limit:
                del interests[interest]

    # normalize the interest counts per user
    for user_id, interests in interest_count.items():
        total = sum(interests.values())
        for interest in interests:
            interests[interest] /= total

    similarity = defaultdict(lambda: defaultdict(float))

    for n in g.nodes():
        neighbors = list(g.neighbors(n))
        if len(interest_count[n].keys()) > 0:
            n_most_frequent_interest = sorted(
                interest_count[n].items(), key=lambda x: x[1], reverse=True
            )
            neighbors_interests = []
            for neighbor in neighbors:
                if len(interest_count[neighbor].keys()) > 0:
                    n_most_frequent_interests = sorted(
                        interest_count[neighbor].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                    neighbors_interests.append(n_most_frequent_interests)

            # compute the percentage of neighbors with the same most frequent interest
            if len(neighbors_interests) > 0:
                similarity[n] = 0

                for ni in neighbors_interests:
                    for iis in ni:
                        if iis[0] in {k[0]: None for k in n_most_frequent_interest}:
                            similarity[n] += 1
                            break

                similarity[n] /= len(neighbors_interests)
    return similarity
