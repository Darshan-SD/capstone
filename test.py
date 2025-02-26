import pandas as pd

def replace_topics_with_ids(topic_id_file, main_file, output_file):
    # Load the topic_id sheet
    topic_df = pd.read_excel(topic_id_file, sheet_name='topic_ids')
    main_df = pd.read_excel(main_file, sheet_name='main')
    
    # Create a dictionary mapping topics to their IDs
    topic_dict = dict(zip(topic_df['Topic'], topic_df['ID']))
    
    # Function to replace topics with their IDs
    def map_topics_to_ids(topic_list):
        topics = [topic.strip() for topic in topic_list.split(',')]
        return ', '.join(str(topic_dict.get(topic, topic)) for topic in topics)
    
    # Apply transformation
    main_df['Topic'] = main_df['Topic'].apply(map_topics_to_ids)
    
    # Save the updated DataFrame to a new file
    main_df.to_excel(output_file, index=False)
    print(f"Updated file saved as {output_file}")

# Example usage
replace_topics_with_ids('aitutor_test_copy.xlsx', 'aitutor_test_copy.xlsx', 'updated_main.xlsx')