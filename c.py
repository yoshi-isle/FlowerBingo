from collections import Counter

import numpy as np


def gini_impurity(class_vector):
    if len(class_vector) == 0:
        return 0.0

    _, counts = np.unique(class_vector, return_counts=True)
    probabilities = counts / len(class_vector)
    return 1.0 - np.sum(probabilities**2)


def gini_gain(previous_classes, current_splits):
    if len(previous_classes) == 0:
        return 0.0

    parent_impurity = gini_impurity(previous_classes)
    weighted_child_impurity = 0.0

    for split in current_splits:
        weighted_child_impurity += (len(split) / len(previous_classes)) * gini_impurity(
            split
        )

    return parent_impurity - weighted_child_impurity


class _DecisionTreeNode:
    def __init__(
        self, feature_index=None, threshold=None, left=None, right=None, label=None
    ):
        self.feature_index = feature_index
        self.threshold = threshold
        self.left = left
        self.right = right
        self.label = label

    def decide(self, feature_row):
        if self.label is not None:
            return self.label

        if feature_row[self.feature_index] <= self.threshold:
            return self.left.decide(feature_row)
        return self.right.decide(feature_row)


class _DecisionTree:
    def __init__(self, depth_limit=5):
        self.depth_limit = depth_limit
        self.root = None

    def fit(self, features, classes, feature_indices):
        self.root = self._build_tree(features, classes, feature_indices, depth=0)
        return self

    def classify(self, features):
        return np.array([self.root.decide(feature_row) for feature_row in features])

    def _build_tree(self, features, classes, feature_indices, depth=0):
        classes = np.asarray(classes).reshape(-1)

        if len(np.unique(classes)) == 1:
            return _DecisionTreeNode(label=classes[0])

        if depth >= self.depth_limit or features.shape[1] == 0:
            return _DecisionTreeNode(label=self._majority_class(classes))

        best_gain = 0.0
        best_feature = None
        best_threshold = None

        for feature_index in feature_indices:
            values = np.unique(features[:, feature_index])

            if len(values) <= 1:
                continue

            for value_index in range(len(values) - 1):
                threshold = (values[value_index] + values[value_index + 1]) / 2.0
                left_mask = features[:, feature_index] <= threshold
                right_mask = ~left_mask

                if not np.any(left_mask) or not np.any(right_mask):
                    continue

                gain = gini_gain(classes, [classes[left_mask], classes[right_mask]])
                if gain > best_gain:
                    best_gain = gain
                    best_feature = feature_index
                    best_threshold = threshold

        if best_feature is None:
            return _DecisionTreeNode(label=self._majority_class(classes))

        left_mask = features[:, best_feature] <= best_threshold
        right_mask = ~left_mask

        left_child = self._build_tree(
            features[left_mask], classes[left_mask], feature_indices, depth + 1
        )
        right_child = self._build_tree(
            features[right_mask], classes[right_mask], feature_indices, depth + 1
        )

        return _DecisionTreeNode(
            feature_index=best_feature,
            threshold=best_threshold,
            left=left_child,
            right=right_child,
        )

    @staticmethod
    def _majority_class(classes):
        values, counts = np.unique(classes, return_counts=True)
        return values[np.argmax(counts)]


class RandomForest:
    """Random forest classification."""

    def __init__(
        self,
        num_trees=200,
        depth_limit=5,
        example_subsample_rate=1,
        attr_subsample_rate=0.3,
    ):
        self.trees = []
        self.num_trees = num_trees
        self.depth_limit = depth_limit
        self.example_subsample_rate = example_subsample_rate
        self.attr_subsample_rate = attr_subsample_rate

    def fit(self, features, classes):
        """Build a random forest using bootstrap aggregation."""
        features = np.asarray(features)
        classes = np.asarray(classes).reshape(-1)

        num_examples, num_features = features.shape
        sample_size = max(1, int(np.ceil(num_examples * self.example_subsample_rate)))
        feature_count = max(1, int(np.ceil(num_features * self.attr_subsample_rate)))
        feature_count = min(feature_count, num_features)

        self.trees = []

        for _ in range(self.num_trees):
            sample_indices = np.random.choice(
                num_examples, size=sample_size, replace=True
            )
            feature_indices = np.random.choice(
                num_features, size=feature_count, replace=False
            )

            sampled_features = features[sample_indices]
            sampled_classes = classes[sample_indices]

            tree = _DecisionTree(depth_limit=self.depth_limit)
            tree.fit(sampled_features, sampled_classes, feature_indices)
            self.trees.append(tree)

        return self

    def classify(self, features):
        """Classify a list of features based on the trained random forest."""
        features = np.asarray(features)

        if not self.trees:
            return np.array([])

        tree_votes = np.array([tree.classify(features) for tree in self.trees])
        votes = []

        for column in tree_votes.T:
            vote_counts = Counter(column)
            winning_label = min(
                vote_counts.items(), key=lambda item: (-item[1], item[0])
            )[0]
            votes.append(winning_label)

        return np.array(votes)
