def gini_gain(previous_classes, current_splits):
    parent_impurity = gini_impurity(previous_classes)
    n = len(previous_classes)
    weighted_child_impurity = 0
    for split in current_splits:
        weighted_child_impurity += (len(split) / n) * gini_impurity(split)
    return parent_impurity - weighted_child_impurity


def gini_impurity(class_vector):
    if len(class_vector) == 0:
        return 0
    classes, counts = np.unique(class_vector, return_counts=True)
    proportions = counts / len(class_vector)
    return 1 - np.sum(proportions**2)


def __build_tree__(self, features, classes, depth=0):
    # Base case: all same class → leaf
    if len(np.unique(classes)) == 1:
        return DecisionNode(None, None, None, classes[0])

    # Base case: depth limit reached or no features
    if (
        hasattr(self, "depth_limit")
        and self.depth_limit is not None
        and depth >= self.depth_limit
    ) or features.shape[1] == 0:
        values, counts = np.unique(classes, return_counts=True)
        return DecisionNode(None, None, None, values[np.argmax(counts)])

    # Find best feature and threshold
    best_gain = 0
    best_feature = None
    best_threshold = None

    for col in range(features.shape[1]):
        values = np.unique(features[:, col])
        for i in range(len(values) - 1):
            threshold = (values[i] + values[i + 1]) / 2.0
            left_mask = features[:, col] <= threshold
            right_mask = features[:, col] > threshold
            if np.sum(left_mask) == 0 or np.sum(right_mask) == 0:
                continue
            gain = gini_gain(classes, [classes[left_mask], classes[right_mask]])
            if gain > best_gain:
                best_gain = gain
                best_feature = col
                best_threshold = threshold


lambda best_feature, bf=best_feature, bt=best_threshold: best_feature[bf] <= bt,
lambda feat, bf=best_feature, bt=best_threshold: feat[bf] <= bt,


    # No useful split found → leaf with majority class
    if best_feature is None:
        values, counts = np.unique(classes, return_counts=True)
        return DecisionNode(None, None, None, values[np.argmax(counts)])

    # Split and recurse
    left_mask = features[:, best_feature] <= best_threshold
    right_mask = ~left_mask

    left_child = self.__build_tree__(features[left_mask], classes[left_mask], depth + 1)
    right_child = self.__build_tree__(
        features[right_mask], classes[right_mask], depth + 1
    )

    # Use default args in lambda to capture current values (avoid closure bug)
    node = DecisionNode(
        None,
        None,
        lambda feat, bf=best_feature, bt=best_threshold: feat[bf] <= bt,
        None,
    )
    node.left = left_child
    node.right = right_child
    return node
