import itertools

class SimilarityProcessor:
    def __init__(self, target_count, reference_array):
        # 存储输入的子列表
        self.input_lists = []
        # 设定要从一维列表中选取的元素个数
        self.target_count = target_count
        # 存储参考数组
        self.reference_array = reference_array

    def add_list(self, new_list):
        # 将新列表添加到输入列表中
        self.input_lists.append(new_list)
        if len(self.input_lists) == 3:
            # 当输入列表达到 3 个时，进行后续处理
            return self.process_lists()
        return None

    def process_lists(self):
        # 将三个列表合并成一维列表
        flat_list = list(itertools.chain(*self.input_lists))
        # 找出相似度最低的 target_count 个元素
        selected_elements = self.select_dissimilar_elements(flat_list)
        return selected_elements

    def select_dissimilar_elements(self, flat_list):
        # 生成所有可能的元素组合，并过滤掉有重复元素的组合
        all_combinations = [comb for comb in itertools.combinations(flat_list, self.target_count) if len(set(comb)) == len(comb)]
        best_combination = None
        max_total_difference = float('-inf')

        for combination in all_combinations:
            # 计算当前组合与参考数组的总差值
            total_difference = self.calculate_total_difference(combination, self.reference_array)
            if total_difference > max_total_difference:
                max_total_difference = total_difference
                best_combination = combination

        return list(best_combination)

    def calculate_total_difference(self, combination, reference_array):
        total_difference = 0
        # 对组合和参考数组进行全排列匹配，找出最大的总差值
        all_permutations = itertools.permutations(combination)
        max_difference = float('-inf')
        for permutation in all_permutations:
            current_difference = sum(abs(a - b) for a, b in zip(permutation, reference_array))
            max_difference = max(max_difference, current_difference)
        return max_difference

    def compare_and_sort(self, selected_elements, reference_array):
        if len(selected_elements) != len(reference_array):
            raise ValueError("两个数组的长度必须相同")
        # 按照参考数组的顺序找到最接近的元素
        sorted_selected_elements = []
        remaining_elements = selected_elements.copy()
        for ref in reference_array:
            closest_element = min(remaining_elements, key=lambda x: abs(x - ref))
            sorted_selected_elements.append(closest_element)
            remaining_elements.remove(closest_element)
        return sorted_selected_elements


# 使用示例
reference_array = [21.4, 1.4, 8.8, 4.5,6.5]
processor = SimilarityProcessor(target_count=5, reference_array=reference_array)

# 添加列表
result1 = processor.add_list([1, 21, 7.8, 4,6])
result2 = processor.add_list([6,4, 1, 7.8, 21])
result3 = processor.add_list([1, 7.8,6, 4, 21])

if result3:
    selected_elements = result3
    sorted_selected_elements = processor.compare_and_sort(selected_elements, reference_array)
    print("选择的元素:", selected_elements)
    print("排序后的元素:", sorted_selected_elements)